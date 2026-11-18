"""Reaction discovery and selection utilities for BOLSIG+ workflows."""

import os
import re

class reactionExtractor:
    """Inspect the LXCat database and collect available reaction metadata."""

    def __init__(self, dataPath):
        """Initialize the reaction extractor.

        Args:
            dataPath (str): Path to the directory that contains the species
                subdirectories with LXCat reaction files.
        """

        self._dataPath = dataPath
        self._availableReactions = dict()
        self.__availableReactionsFilename = str()

    def __extractReaction(self, speciesDir, filename):
        """Extract the reaction label from a reaction file.

        Args:
            speciesDir (str): Species subdirectory name inside `self._dataPath`.
            filename (str): Reaction file name to inspect.

        Returns:
            str: Reaction description read from the `PROCESS:` entry, or `"NA"`
            when the entry is not present.
        """

        identifier = "PROCESS:"
        with open(os.path.join(self._dataPath,speciesDir,filename), 'r') as file:
            for line in file:
                if line.startswith(identifier):
                    return line.split(identifier)[1].strip()
        return 'NA'
    
    def __extractEnergy(self, speciesDir, filename):
        """Extract the activation energy from a reaction file.

        Args:
            speciesDir (str): Species subdirectory name inside `self._dataPath`.
            filename (str): Reaction file name to inspect.

        Returns:
            str: Energy value that appears immediately before the `eV` token, or
            `"--"` when no energy is declared.
        """

        identifier = "PARAM.:"
        with open(os.path.join(self._dataPath, speciesDir, filename), 'r') as file:
            for line in file:
                if line.startswith(identifier):
                    tokens = line.split()
                    for i, token in enumerate(tokens):
                        if token.strip().lower().rstrip(',:;.') == "ev" and i > 0:
                            return tokens[i - 1]
                    return '--'
        return '--'
    
    def __extractDatabase(self, speciesDir, filename):
        """Extract the source database name from a reaction file.

        Args:
            speciesDir (str): Species subdirectory name inside `self._dataPath`.
            filename (str): Reaction file name to inspect.

        Returns:
            str: Database identifier declared in the `DATABASE:` entry, or
            `"--"` when the entry is missing.
        """

        identifier = "DATABASE:"
        with open(os.path.join(self._dataPath, speciesDir, filename), 'r') as file:
            for line in file:
                if line.startswith(identifier):
                    return line.split(identifier)[1].strip()
        return '--'
    
    @staticmethod
    def __naturalKey(string):
        """Build a natural-sort key for file names containing digits.

        Args:
            string (str): String to split into text and numeric components.

        Returns:
            list: Mixed text and integer tokens suitable for natural sorting.
        """

        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]
    
    def findReactions(self):
        """Scan the LXCat database and populate the available-reactions map.

        Returns:
            dict: Nested dictionary keyed by species name with reaction metadata
            fields `ID`, `file`, `reaction`, `energy`, and `database`.
        """

        reactionDir = sorted(os.listdir(self._dataPath))
        
        reactionDir = [entry for entry in reactionDir if os.path.isdir(os.path.join(self._dataPath, entry))]

        for sp in reactionDir:
            reactionsFiles = sorted(os.listdir(os.path.join(self._dataPath, sp)), key=self.__naturalKey)
            self._availableReactions[sp] = dict()
            self._availableReactions[sp]['ID'] = list()
            self._availableReactions[sp]['file'] = list()
            self._availableReactions[sp]['reaction'] = list()
            self._availableReactions[sp]['energy'] = list()
            self._availableReactions[sp]['database'] = list()

            reactionNum = 0
            for r in reactionsFiles:
                reactionNum += 1
                self._availableReactions[sp]['ID'].append(reactionNum)
                self._availableReactions[sp]['file'].append(r)
                self._availableReactions[sp]['reaction'].append(self.__extractReaction(sp, r))
                self._availableReactions[sp]['energy'].append(self.__extractEnergy(sp, r))
                self._availableReactions[sp]['database'].append(self.__extractDatabase(sp, r))
        return self._availableReactions
    

    # # Print available reactions to screen
    # # -----------------------------------
    # def printAvailableReactions(self):
    #     # Define headers
    #     headers = ['ID', 'Reaction', 'Energy', 'File']

    #     # Specify the length of each header (for Reaction header find the longest string and add more 5 spaces)
    #     lengthID = 6
    #     lengthEnergy = 10
    #     lengthFile = 20
    #     longestReaction = str()
    #     for sp in self._availableReactions.values():
    #         for reaction in sp['reaction']:
    #             # Update longest_reaction if the current reaction is longer
    #             if len(reaction) > len(longestReaction):
    #                 longestReaction = reaction
    #     lengthReaction = len(longestReaction) + 5

    #     # Print info
    #     print(f'The available reactions for BOLSIG+ are:')

    #     # Print headers
    #     print(f'{headers[0]:<{lengthID}} {headers[1]:<{lengthReaction}} {headers[2]:<{lengthEnergy}} {headers[3]:<{lengthFile}}')

    #     # Print a line separator
    #     separatorChar = '='
    #     print(f'{separatorChar*len(headers[0])}{' '*(lengthID-len(headers[0]))} {separatorChar*len(headers[1])}{' '*(lengthReaction-len(headers[1]))} {separatorChar*len(headers[2])}{' '*(lengthEnergy-len(headers[2]))} {separatorChar*len(headers[3])}{' '*(lengthFile-len(headers[3]))}')

    #     # Populate rows
    #     for sp, entry in self._availableReactions.items():
    #         for i in range(len(entry['ID'])):
    #             print(f'{entry['ID'][i]:<{lengthID}} {entry['reaction'][i]:<{lengthReaction}} {entry['energy'][i]:<{lengthEnergy}} ./{os.path.join(os.path.basename(self._dataPath), sp, entry['file'][i])}')
    #         print(f'')


    def writeAvailableReactions(self, filename):
        """Write a formatted summary of all available reactions to disk.

        Args:
            filename (str): Name of the summary file written inside
                `self._dataPath`.
        """

        self.__availableReactionsFilename = filename
        headers = ['ID', 'Reaction', 'Energy', 'Database', 'File']

        lengthID = 6
        lengthEnergy = 12
        lengthFile = 10

        longestDatabase = str()
        for sp in self._availableReactions.values():
            for database in sp['database']:
                if len(database) > len(longestDatabase):
                    longestDatabase = database
        lengthDatabase = len(longestDatabase) + 5

        longestReaction = str()
        for sp in self._availableReactions.values():
            for reaction in sp['reaction']:
                if len(reaction) > len(longestReaction):
                    longestReaction = reaction
        lengthReaction = len(longestReaction) + 5

        with open(os.path.join(self._dataPath, self.__availableReactionsFilename), 'w') as file:
            file.write(f'{headers[0]:<{lengthID}} {headers[1]:<{lengthReaction}} {headers[2]:<{lengthEnergy}} {headers[3]:<{lengthDatabase}} {headers[4]:<{lengthFile}}\n')
            
            separatorChar = '='
            file.write(f'{separatorChar*len(headers[0])}{" " * (lengthID-len(headers[0]))} {separatorChar*len(headers[1])}{" " * (lengthReaction-len(headers[1]))} {separatorChar*len(headers[2])}{" " * (lengthEnergy-len(headers[2]))} {separatorChar*len(headers[3])}{" " * (lengthDatabase-len(headers[3]))} {separatorChar*len(headers[4])}{" " * (lengthFile-len(headers[4]))}\n')            
            for sp, entry in self._availableReactions.items():
                for i in range(len(entry['ID'])):
                    file.write(f'{entry["ID"][i]:<{lengthID}} {entry["reaction"][i]:<{lengthReaction}} {entry["energy"][i]:<{lengthEnergy}} {entry["database"][i]:<{lengthDatabase}} ./{os.path.join(os.path.basename(self._dataPath), sp, entry["file"][i])}\n')
                file.write(f'\n')


class reactionSelector:
    """Resolve the reaction subset requested by a case input file."""

    def __init__(self, reactionExtractorObj, inputFilePath):
        """Initialize the selector for a specific case input file.

        Args:
            reactionExtractorObj (reactionExtractor): Extractor instance that
                already contains the available reaction metadata.
            inputFilePath (str): Path to the case input file.
        """

        self._inputFilePath = inputFilePath
        self._inputFileName = os.path.basename(self._inputFilePath)
        self._dataPath = reactionExtractorObj._dataPath
        self._availableReactions = reactionExtractorObj._availableReactions
        self._inputDirPath = os.path.dirname(self._inputFilePath)
        self._selectedReactions = dict()

    def __extractReactionsFromLiterature(self, filename, keyword):
        """Load reaction IDs from a literature reference list.

        Args:
            filename (str): Path to the literature mapping file.
            keyword (str): Literature key to search for, without the trailing
                colon.

        Returns:
            dict: Nested dictionary with the same structure as
            `self._availableReactions`, but containing only the selected
            reactions.

        Raises:
            Exception: If the literature key is not found in the mapping file.
        """

        selectedReactionsLocalDict = dict()
        keywordFound = False

        with open(filename, 'r') as file:
            lines = file.readlines()

            for lineNumber, line in enumerate(lines):
                line = line.strip()

                if line.startswith('#') or not line.strip():
                    continue

                if line.startswith(keyword+':'):
                    keywordFound = True
                    tempLine = line.split(':')
                    tempLine = tempLine[1].split(',')
                    reactionsList = [int(s.strip()) for s in tempLine]

                    for sp, values in self._availableReactions.items():
                        selectedReactionsLocalDictValues = {'ID': [], 'file': [], 'reaction': [],  'energy': [],  'database': []}
                        for i, reactionID in enumerate(values['ID']):
                            if reactionID in reactionsList:
                                selectedReactionsLocalDictValues['ID'].append(reactionID)
                                selectedReactionsLocalDictValues['file'].append(values['file'][i])
                                selectedReactionsLocalDictValues['reaction'].append(values['reaction'][i])
                                selectedReactionsLocalDictValues['energy'].append(values['energy'][i])
                                selectedReactionsLocalDictValues['database'].append(values['database'][i])
                        if selectedReactionsLocalDictValues['ID']:
                            selectedReactionsLocalDict[sp] = selectedReactionsLocalDictValues
                    break

        if not keywordFound:
            raise Exception(f"Keyword: {keyword+':'}: was not found in file: {filename}.")

        return selectedReactionsLocalDict

    def readInputFile(self):
        """Read the case input file and populate the selected reaction set.

        Supported selection modes are `custom`, `allAvailable`, and
        `literature`.

        Raises:
            Exception: If the selection block is malformed or references
            unavailable reactions.
        """

        selectionMethod = str()
        with open(self._inputFilePath, 'r') as file:
            lines = file.readlines()
            
            for lineNumber, line in enumerate(lines):
                line = line.strip()
                
                if line.startswith('#') or not line.strip():
                    continue

                if line.startswith('selectReactionMethod'):
                    if len(line.split()) > 2:
                        raise Exception(f'File:"{self._inputFilePath}". Invalid input in line: {lineNumber}')
                    else:
                        selectionMethod = line.split()[1]

                        # For 'custom' keyword
                        # if selectionMethod == 'custom':
                        #     for i in range(lineNumber+1, len(lines)):
                        #         lines[i] = lines[i].strip() # Get rid of trailing newline character (\n)
                        #         tempLine = lines[i].split() # Create this list only for the following if statement
                        #         if tempLine and tempLine[0].endswith(':'):
                        #             tempLine = str() # Repurpose the previous string to assign 
                        #             tempLine = lines[i].split(':',1)
                        #             sp = tempLine[0].strip()
                        #             tempReactions = tempLine[1].strip()
                        #             self._selectedReactions[sp] = dict()
                        #             self._selectedReactions[sp]['ID'] = [int(s.strip()) for s in tempReactions.split(',')]
                        #             self._selectedReactions[sp]['file'] = [file for i, file in zip(self._availableReactions[sp]['ID'], self._availableReactions[sp]['file']) if i in self._selectedReactions[sp]['ID']]
                        #             self._selectedReactions[sp]['reaction'] = [file for i, file in zip(self._availableReactions[sp]['ID'], self._availableReactions[sp]['reaction']) if i in self._selectedReactions[sp]['ID']]
                        #             self._selectedReactions[sp]['energy'] = [file for i, file in zip(self._availableReactions[sp]['ID'], self._availableReactions[sp]['energy']) if i in self._selectedReactions[sp]['ID']]
                        #             self._selectedReactions[sp]['database'] = [file for i, file in zip(self._availableReactions[sp]['ID'], self._availableReactions[sp]['database']) if i in self._selectedReactions[sp]['ID']]
                                    


                        if selectionMethod == 'custom':
                            for i in range(lineNumber + 1, len(lines)):
                                lines[i] = lines[i].strip()
                                tempLine = lines[i].split()
                                if tempLine and tempLine[0].endswith(':'):
                                    spLine = lines[i].split(':', 1)
                                    sp = spLine[0].strip()
                                    idList = [int(s.strip()) for s in spLine[1].strip().split(',')]
                                    self._selectedReactions[sp] = {key: [] for key in ['ID', 'file', 'reaction', 'energy', 'database']}

                                    for rid in idList:
                                        try:
                                            idx = self._availableReactions[sp]['ID'].index(rid)
                                        except ValueError:
                                            raise Exception(f'Reaction ID {rid} for species "{sp}" not found in available reactions.')

                                        self._selectedReactions[sp]['ID'].append(rid)
                                        self._selectedReactions[sp]['file'].append(self._availableReactions[sp]['file'][idx])
                                        self._selectedReactions[sp]['reaction'].append(self._availableReactions[sp]['reaction'][idx])
                                        self._selectedReactions[sp]['energy'].append(self._availableReactions[sp]['energy'][idx])
                                        self._selectedReactions[sp]['database'].append(self._availableReactions[sp]['database'][idx])





                                # Uncomment the else statement if you want to stop skipping empty lines between the reactions in the input file
                                # else: 
                                #     break
                        elif selectionMethod == 'allAvailable':
                            self._selectedReactions = self._availableReactions
                        elif selectionMethod == 'literature':
                            tempLine = lines[lineNumber+1].split()

                            if len(tempLine)!=2:
                                raise Exception(f'File:"{self._inputFileName}". Arguments for selectionMethod "{selectionMethod}" must be exactly 2. The filename and the paper keyword.')

                            literatureDataFile = tempLine[0]
                            literaturePaperKeyword = tempLine[1]
                            self._selectedReactions = self.__extractReactionsFromLiterature(os.path.join(self._dataPath,literatureDataFile), literaturePaperKeyword)
                        else:
                            raise Exception(f'File:"{self._inputFileName}". Unknown input "{selectionMethod}". Available options are "allAvailable", "literature" or "custom"')
                    
                    break
                else:
                    raise Exception(f'File:"{self._inputFileName}". The selectReactionMethod entry not found.')
    
    def createCrossSectionFile(self, filename):
        """Create the combined cross-section file used by BOLSIG+.

        Args:
            filename (str): Name of the generated cross-section file placed in
                the case `bolsigFiles` directory.
        """

        self._crossSectionFileName = filename
        self._bolsigInputDirName = 'bolsigFiles'
        os.makedirs(os.path.join(self._inputDirPath, self._bolsigInputDirName), exist_ok=True)
        self._crossSectionFilePath = os.path.join(self._inputDirPath, self._bolsigInputDirName, self._crossSectionFileName)
        fileList = list()

        with open(self._crossSectionFilePath, 'w') as fout:
            fout.write('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n')

            for sp in self._selectedReactions.keys():
                fileList = self._selectedReactions[sp]['file']
                fout.write('********************************************************** ')
                fout.write(sp)
                fout.write(' **********************************************************\n\n')
                for file in fileList:
                    with open(os.path.join(self._dataPath, sp, file), 'r') as fin:
                        fout.write(fin.read())
                        fout.write('\n')
                        
            fout.write('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')


    def _printSelectedReactions(self):
        """Print a formatted summary of the selected reactions to stdout."""

        # Define headers
        headers = ['ID', 'Reaction', 'Energy', 'Database', 'File']

        # Specify the length of each header (for Reaction header find the longest string and add more 5 spaces)
        lengthID = 6
        lengthEnergy = 12
        lengthFile = 10

        longestDatabase = str()
        for sp in self._selectedReactions.values():
            for database in sp['database']:
                if len(database) > len(longestDatabase):
                    longestDatabase = database
        lengthDatabase = len(longestDatabase) + 5

        longestReaction = str()
        for sp in self._selectedReactions.values():
            for reaction in sp['reaction']:
                if len(reaction) > len(longestReaction):
                    longestReaction = reaction
        lengthReaction = len(longestReaction) + 5

        print(f'The selected reactions for BOLSIG+ are:\n')

        print(f'{headers[0]:<{lengthID}} {headers[1]:<{lengthReaction}} {headers[2]:<{lengthEnergy}} {headers[3]:<{lengthDatabase}} {headers[4]:<{lengthFile}}')

        separatorChar = '='
        print(f'{separatorChar*len(headers[0])}{" "*(lengthID-len(headers[0]))} {separatorChar*len(headers[1])}{" "*(lengthReaction-len(headers[1]))} {separatorChar*len(headers[2])}{" "*(lengthEnergy-len(headers[2]))} {separatorChar*len(headers[3])}{" "*(lengthDatabase-len(headers[3]))} {separatorChar*len(headers[4])}{" "*(lengthFile-len(headers[4]))}')

        for sp, entry in self._selectedReactions.items():
            for i in range(len(entry['ID'])):
                print(f'{entry["ID"][i]:<{lengthID}} {entry["reaction"][i]:<{lengthReaction}} {entry["energy"][i]:<{lengthEnergy}} {entry["database"][i]:<{lengthDatabase}} ./{os.path.join(os.path.basename(self._dataPath), sp, entry["file"][i])}')
            print(f'')

    def writeSelectedReactions(self, filename):
        """Write a formatted summary of the selected reactions to disk.

        Args:
            filename (str): Name of the output file written in the case
                directory.
        """

        self._selectedReactionsFileName = filename
        self._selectedReactionsFilePath = os.path.join(self._inputDirPath, self._selectedReactionsFileName)

        # Define headers
        headers = ['ID', 'Reaction', 'Energy', 'Database', 'File']

        # Specify the length of each header (for Reaction header find the longest string and add more 5 spaces)
        lengthID = 6
        lengthEnergy = 12
        lengthFile = 10

        longestDatabase = str()
        for sp in self._selectedReactions.values():
            for database in sp['database']:
                if len(database) > len(longestDatabase):
                    longestDatabase = database
        lengthDatabase = len(longestDatabase) + 5

        longestReaction = str()
        for sp in self._selectedReactions.values():
            for reaction in sp['reaction']:
                if len(reaction) > len(longestReaction):
                    longestReaction = reaction
        lengthReaction = len(longestReaction) + 5

        with open(self._selectedReactionsFilePath, 'w') as file:
            file.write(f'The selected reactions for BOLSIG+ are:\n\n')
            
            file.write(f'{headers[0]:<{lengthID}} {headers[1]:<{lengthReaction}} {headers[2]:<{lengthEnergy}} {headers[3]:<{lengthDatabase}} {headers[4]:<{lengthFile}}\n')
            
            separatorChar = '='
            file.write(f'{separatorChar*len(headers[0])}{" " * (lengthID-len(headers[0]))} {separatorChar*len(headers[1])}{" " * (lengthReaction-len(headers[1]))} {separatorChar*len(headers[2])}{" " * (lengthEnergy-len(headers[2]))} {separatorChar*len(headers[3])}{" " * (lengthDatabase-len(headers[3]))} {separatorChar*len(headers[4])}{" " * (lengthFile-len(headers[4]))}\n')
            
            for sp, entry in self._selectedReactions.items():
                for i in range(len(entry['ID'])):
                    file.write(f'{entry["ID"][i]:<{lengthID}} {entry["reaction"][i]:<{lengthReaction}} {entry["energy"][i]:<{lengthEnergy}} {entry["database"][i]:<{lengthDatabase}} ./{os.path.join(os.path.basename(self._dataPath), sp, entry["file"][i])}\n')
                file.write(f'\n')

                
