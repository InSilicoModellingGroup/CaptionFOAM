"""High-level orchestration for preparing and running BOLSIG+ cases."""

import os
from LXCatDataHandler import reactionExtractor, reactionSelector
from bolsigInputHandler import bolsigExecutor 
from bolsigOutputHandler import bolsigOutputReader 


def runBolsigMain(projectPath, inputFilePath):
    """Run the full BOLSIG+ workflow for a case input file.

    Args:
        projectPath (str): Path to the BOLSIG utility directory that contains
            the `LXCatData` database.
        inputFilePath (str): Path to the case-specific input file.
    """

    # Discover the available reaction database entries.
    LXCatDataPath = os.path.join(projectPath, 'LXCatData')
    LXCatData = reactionExtractor(LXCatDataPath)
    LXCatData.findReactions()
    LXCatData.writeAvailableReactions('availableReactions.txt')

    # Select the subset of reactions requested by the case input.
    selectReactions = reactionSelector(LXCatData, inputFilePath)
    selectReactions.readInputFile()
    selectReactions.createCrossSectionFile('crossSections.txt')
    selectReactions.writeSelectedReactions('selectedReactions.txt')

    # Build the BOLSIG+ input deck and execute the solver.
    bolsigInput = bolsigExecutor(selectReactions, 'bolsigInput.dat')
    bolsigInput.writeBolsigInput()
    bolsigInput.runBolsigCode()

    # Parse solver output and export the processed coefficients.
    bolsigData = bolsigOutputReader(bolsigInput)
    bolsigData.processFile()
    bolsigData.writeResults('openfoam', 'bolsigProperties')

    print('\nEND')
