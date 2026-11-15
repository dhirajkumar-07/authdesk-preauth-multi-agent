import os, sys
subfolder = os.path.join(os.path.dirname(__file__), "authdesk-kit")
if os.path.exists(subfolder):
    sys.path.insert(0, subfolder)
    os.chdir(subfolder)

import evaluate
if __name__ == "__main__":
    evaluate.main()

