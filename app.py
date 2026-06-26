import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import traceback

# === CONFIGURATION TIKTOKEN POUR LE HORS-LIGNE ===
dossier_base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
os.environ["TIKTOKEN_CACHE_DIR"] = os.path.join(dossier_base, "tiktoken_cache")
# =======================================================

def obtenir_port_depuis_fcc():
    """Lit le fichier ~/.fcc/.env ou %USERPROFILE%\.fcc\.env pour récupérer le port."""
    home = os.path.expanduser("~")
    chemin_env = os.path.join(home, ".fcc", ".env")
    port_defaut = "8082"
    
    if os.path.exists(chemin_env):
        try:
            with open(chemin_env, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("PORT="):
                        valeur = line.split("=")[1].strip()
                        return valeur.replace('"', '').replace("'", "")
        except Exception as e:
            print(f"Erreur lors de la lecture de ~/.fcc/.env : {e}")
            
    return port_defaut

def selectionner_dossier():
    """Affiche le sélecteur de dossier et le force au tout premier plan."""
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.attributes("-topmost", True)
    root.update()
    
    dossier = filedialog.askdirectory(title="Sélectionnez votre dossier de travail", parent=root)
    root.destroy()
    
    if not dossier:
        print("Aucun dossier sélectionné, fermeture.")
        sys.exit()
    return dossier

def demarrer_serveur_interne(port):
    """Démarre le serveur FastAPI de free-claude-code directement dans ce processus."""
    try:
        import uvicorn
        from server import app
        uvicorn.run(app, host="127.0.0.1", port=int(port), log_level="warning")
    except Exception as e:
        print(f"Erreur critique du serveur proxy interne : {e}")
        with open("fcc_server_error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)

def lancer_systeme():
    dossier_travail = selectionner_dossier()
    port = obtenir_port_depuis_fcc()

    # Configuration des variables d'environnement pour Claude Code
    os.environ["ANTHROPIC_BASE_URL"] = f"http://localhost:{port}"
    os.environ["ANTHROPIC_API_KEY"] = "fake-key-pour-passer-les-verifications"

    # Lancement du serveur proxy dans un Thread d'arrière-plan autonome
    print(f"Démarrage du proxy local sur le port {port}...")
    server_thread = threading.Thread(
        target=demarrer_serveur_interne, 
        args=(port,), 
        daemon=True
    )
    server_thread.start()

    # On attend 2 secondes que le serveur s'initialise
    time.sleep(2)

    # Détection des fichiers Node et Claude Code embarqués (mode portable autonome)
    chemin_node_embarque = os.path.join(dossier_base, "node.exe")
    chemin_claude_embarque = os.path.join(dossier_base, "claude-cli.js")
    mode_portable_actif = os.path.exists(chemin_node_embarque) and os.path.exists(chemin_claude_embarque)

    # Lancement de l'agent Claude Code
    print(f"Ouverture de Claude Code dans : {dossier_travail}")
    try:
        if sys.platform == "win32" and mode_portable_actif:
            print("Mode portable détecté : Lancement de Node.js et Claude Code embarqués...")
            # On utilise le drapeau CREATE_NEW_CONSOLE pour forcer Windows à ouvrir 
            # un terminal natif indépendant de manière propre pour notre Node.js embarqué
            subprocess.run(
                [chemin_node_embarque, chemin_claude_embarque],
                cwd=dossier_travail,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        elif sys.platform == "win32":
            # Mode non-portable : On dépend du système de l'ordinateur
            subprocess.run(
                ["cmd", "/c", "start", "/wait", "cmd", "/c", "fcc-claude"],
                cwd=dossier_travail
            )
        else:
            # Linux (Ubuntu)
            try:
                subprocess.run(["x-terminal-emulator", "-e", "fcc-claude"], cwd=dossier_travail)
            except FileNotFoundError:
                subprocess.run(["fcc-claude"], cwd=dossier_travail)
                
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Impossible de lancer Claude Code. Le moteur Node.js embarqué ou l'agent est introuvable. "
            f"(Détails: {e})"
        )
    finally:
        print("\nFermeture du proxy et nettoyage...")
        print("Système arrêté.")

if __name__ == "__main__":
    try:
        lancer_systeme()
    except Exception as e:
        dossier_exe = os.path.dirname(os.path.realpath(sys.argv[0]))
        chemin_log = os.path.join(dossier_exe, "fcc_debug.log")
        
        try:
            with open(chemin_log, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception as log_err:
            print(f"Impossible d'écrire le fichier de log : {log_err}")

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror(
            "Erreur de fonctionnement",
            f"L'application a rencontré un problème :\n\n{e}\n\n"
            f"Les détails techniques ont été enregistrés dans :\n{chemin_log}"
        )
        root.destroy()
