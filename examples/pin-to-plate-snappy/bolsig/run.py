import sys
import os

# Define input filename
inputFile = 'input.txt'

# Define current path
currenPath = os.path.dirname(os.path.abspath(__file__))

# Define CaptionFOAM utilities path (exported by CaptionFOAM's etc/bashrc)
utilitiesPath = os.environ.get('CAPTIONFOAM_UTILITIES')
if not utilitiesPath:
    sys.exit("Error: CAPTIONFOAM_UTILITIES not set. Source CaptionFOAM's etc/bashrc first.")

# Define src and runBolsig paths
bolsigPath = os.path.abspath(os.path.join(utilitiesPath, 'bolsig'))
LXCatPath = os.path.abspath(os.path.join(bolsigPath, 'LXCatData'))
runBolsigPath = os.path.abspath(os.path.join(bolsigPath, 'runBolsig'))

# Check if BOLSIG directory exists
bolsigExecutablePath = os.path.join(runBolsigPath,'bolsigExe','bolsigminus')
if not os.path.isfile(bolsigExecutablePath):
    print('BOLSIG+ executable not detected. Downloading now...')
    os.system(os.path.join(bolsigPath,'downloadBolsigLinux.sh'))

# Enable to import classes/modules from the src directory
sys.path.insert(0, runBolsigPath)

# Import runBolsig module
from runBolsig import runBolsigMain

# Run all BOLSIG+ related actions
if __name__ == "__main__":
    runBolsigMain(bolsigPath, os.path.join(currenPath, inputFile))

