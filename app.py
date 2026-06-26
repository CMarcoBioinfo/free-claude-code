import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import traceback

# === CONFIGURATION TIKTOKEN POUR LE HORS-LIGNE (CHU) ===
# On redirige le dossier de cache de tiktoken vers le répertoire temporaire de l'exécutable
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
        # En important 'server' directement, PyInstaller comprend qu'il doit 
        # inclure tout free-claude-code (FastAPI, Uvicorn, etc.) dans l'exécutable !
        import uvicorn
        from server import app
        
        # Lancement du serveur uvicorn en local
        uvicorn.run(app, host="127.0.0.1", port=int(port), log_level="warning")
    except Exception as e:
        print(f"Erreur critique du serveur proxy interne : {e}")
        # Écrit l'erreur du serveur dans un fichier pour le debug
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
        daemon=True # daemon=True permet de couper le thread dès que le script principal s'arrête
    )
    server_thread.start()

    # On attend 2 secondes que le serveur s'initialise
    time.sleep(2)

    # Démarrage de l'agent Claude Code
    print(f"Ouverture de Claude Code dans : {dossier_travail}")
    try:
        if sys.platform == "win32":
            # Windows : lance l'invite de commande, attend qu'elle se ferme, puis continue
            result = subprocess.run(
                ["cmd", "/c", "start", "/wait", "cmd", "/c", "fcc-claude"],
                cwd=dossier_travail
            )
            if result.returncode != 0:
                raise RuntimeError("Le terminal Windows a renvoyé une erreur ou a été bloqué.")
        else:
            # Linux (Ubuntu)
            try:
                subprocess.run(["x-terminal-emulator", "-e", "fcc-claude"], cwd=dossier_travail)
            except FileNotFoundError:
                subprocess.run(["fcc-claude"], cwd=dossier_travail)
                
    except FileNotFoundError:
        # Fallback si fcc-claude n'est pas global (on tente avec npx)
        print("fcc-claude non trouvé, tentative avec npx...")
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["cmd", "/c", "start", "/wait", "cmd", "/c", "npx @anthropic-ai/claude-code"],
                    cwd=dossier_travail
                )
            else:
                try:
                    subprocess.run(["x-terminal-emulator", "-e", "npx @anthropic-ai/claude-code"], cwd=dossier_travail)
                except FileNotFoundError:
                    subprocess.run(["npx", "@anthropic-ai/claude-code"], cwd=dossier_travail)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Impossible de lancer Claude Code. Node.js (npx) ou fcc-claude ne semblent pas installés "
                f"sur cet ordinateur. (Erreur: {e})"
            )
    finally:
        # Nettoyage automatique : Pas besoin de "kill" de processus car le thread est "daemon"
        # et s'éteindra automatiquement à la fin de la fonction main
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
