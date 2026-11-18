"""Utilities for constructing and executing BOLSIG+ input decks."""

import os
import platform

class bolsigExecutor:
    """Build BOLSIG+ input files and execute the solver for one case."""
    
    def __init__(self, reactionSelectorObj, filename):
        """Initialize the executor from a populated reaction selector.

        Args:
            reactionSelectorObj (reactionSelector): Selector instance that
                already contains the chosen reactions and output paths.
            filename (str): Name of the BOLSIG+ input file to generate.
        """

        self._bolsigInputFileName = filename
        self._crossSectionFileName = reactionSelectorObj._crossSectionFileName
        self._crossSectionFilePath = reactionSelectorObj._crossSectionFilePath
        self._selectedReactions = reactionSelectorObj._selectedReactions
        self._inputFilePath = reactionSelectorObj._inputFilePath
        self._inputDirPath = reactionSelectorObj._inputDirPath
        self._inputFileName = reactionSelectorObj._inputFileName
        self._bolsigInputDirName = reactionSelectorObj._bolsigInputDirName
        self.__bolsigInputFilePath = os.path.join(self._inputDirPath, reactionSelectorObj._bolsigInputDirName, self._bolsigInputFileName)
        self.__bolsigRunType = 0 # 0=single run, 1=RUNSERIES, 2=RUN2D with composition and a primary sweep
        self._bolsigOuputFileName = 'bolsigOutput.dat'
        self._printSelectedReactions = reactionSelectorObj._printSelectedReactions

    def _readInputFile(self, keyword, multipleEntries = False):
        """Read the values that follow a keyword in the case input file.

        Args:
            keyword (str): Keyword to search for in the input file.
            multipleEntries (bool, optional): Whether multiple lines with the
                same keyword are allowed. Defaults to `False`.

        Returns:
            list: List of token strings for a single entry, or a list of token
            lists when `multipleEntries` is `True`.

        Raises:
            Exception: If multiple single-value entries are found for a keyword
            that is expected to appear only once.
        """

        count = 0
        entry = list()
        singleEntry = list()
        with open(self._inputFilePath, 'r') as file:
            lines = file.readlines()

            for lineNumber, line in enumerate(lines):
                # Remove white spaces at begging and end of line
                line = line.strip()

                # Ignore commented lines and empty lines
                if line.startswith('#') or not line.strip():
                    continue

                # Find the keyword
                tokens = line.split()
                if tokens and tokens[0] == keyword:
                    count += 1
                    singleEntry = tokens
                    singleEntry.pop(0)
                    if not multipleEntries: 
                        entry = singleEntry
                        if count>1:
                            raise Exception(f'More than one entry for keyword"{keyword}" was found in line {lineNumber+1}. File: {self._inputFileName} \nTo allow multiple entries enable the "multipleEntries" argument')
                    else:
                        entry.append(singleEntry)
        return entry # Outputs list for single entry, or list of lists for multiple entries

    @staticmethod
    def __tabs(num = 6):
        """Return a string containing `num` tab characters.

        Args:
            num (int, optional): Number of tabs to generate. Defaults to `6`.

        Returns:
            str: Tab padding used to format BOLSIG+ input files.
        """

        return '\t'*num
    
    def __detectPrimarySweepVariable(self):
        """Infer the primary sweep variable from the case input file.

        The input file may define either one or more `E/N` entries or one or
        more `em` entries. Mixed use is not allowed.

        Raises:
            Exception: If neither keyword is provided, or if both appear in the
            same input file.
        """

        electricFieldEntries = self._readInputFile('E/N', multipleEntries=True)
        meanEnergyEntries = self._readInputFile('em', multipleEntries=True)

        if electricFieldEntries and meanEnergyEntries:
            raise Exception(
                f'Keywords "E/N" and "em" cannot both be used in the same input file. '
                f'Choose only one primary sweep variable. File: {self._inputFileName}'
            )

        if electricFieldEntries:
            self._primarySweepKeyword = 'E/N'
            self._primarySweepVariable = 1
            return electricFieldEntries

        if meanEnergyEntries:
            self._primarySweepKeyword = 'em'
            self._primarySweepVariable = 2
            return meanEnergyEntries

        raise Exception(
            f'Either keyword "E/N" or keyword "em" must be provided. File: {self._inputFileName}'
        )

    def __readPrimarySweepEntries(self):
        """Read and validate the primary sweep definition for the case.

        The sweep variable is inferred from the presence of either the `E/N`
        or `em` keyword in the case input file.

        Raises:
            Exception: If the required sweep definition is missing or does not
            follow the expected value format.
        """

        primarySweepEntries = self.__detectPrimarySweepVariable()

        self._primarySweepEntries = list()
        for entry in primarySweepEntries:
            if len(entry) == 1:
                if self._primarySweepKeyword == 'em':
                    raise Exception(
                        f'Keyword "{self._primarySweepKeyword}" must be followed by 4 values when '
                        f'it is used as the primary sweep variable. File: {self._inputFileName}'
                    )
                self._primarySweepEntries.append([float(entry[0])])
            elif len(entry) == 4:
                parsedEntry = [float(entry[0]), float(entry[1]), int(entry[2]), entry[3]]
                if parsedEntry[3] not in ['linear', 'quadratic', 'exponential']:
                    raise Exception(
                        f'{self._primarySweepKeyword} grid spacing entry must be: "linear", "quadratic" '
                        f'or "exponential". Found "{parsedEntry[3]}". File: {self._inputFileName}'
                    )
                self._primarySweepEntries.append(parsedEntry)
                if self.__bolsigRunType == 0:
                    self.__bolsigRunType += 1
            else:
                validEntries = '1 or 4' if self._primarySweepKeyword == 'E/N' else '4'
                raise Exception(
                    f'{self._primarySweepKeyword} keyword must be followed by {validEntries} values. '
                    f'Found {len(entry)}. File: {self._inputFileName}'
                )

    def __validatePrimarySweepEntries(self):
        """Ensure sweep entries are compatible with multi-run configurations.

        Raises:
            Exception: If `RUNSERIES` or `RUN2D` would be requested with an
            incomplete sweep specification.
        """

        if self.__bolsigRunType == 0:
            return

        for entry in self._primarySweepEntries:
            if len(entry) != 4:
                raise Exception(
                    f'Keyword "{self._primarySweepKeyword}" must be followed by 4 values when '
                    f'RUNSERIES or RUN2D is used. File: {self._inputFileName}'
                )

    def __writeElectricFieldInputEntries(self, file):
        """Write the electric-field condition entry to the BOLSIG+ file.

        Args:
            file: Open file handle for the generated BOLSIG+ input deck.
        """

        self.__readPrimarySweepEntries()

        # BOLSIG+ always expects the electric field condition entry, even when
        # the series variable is the mean electron energy.
        file.write('{:g}{}/ Electric field / N (Td)\n'.format(self._primarySweepEntries[0][0], self.__tabs()))

    def __writeGasCompositionInputEntries(self, file):
        """Write gas-composition values to the BOLSIG+ file.

        Args:
            file: Open file handle for the generated BOLSIG+ input deck.

        Raises:
            Exception: If the gas-composition section is inconsistent with the
            selected reaction set or with the supported sweep formats.
        """

        # Gas composition
        gasComposition = self._readInputFile('gasComposition') # read whole entry of input file
        gasComposition = ' '.join(gasComposition) # make all entries a single string
        gasComposition = gasComposition.split(',') # force split using commas
        gasComposition = filter(None, gasComposition) # filter out empty elements
        gasComposition = [sp.strip() for sp in gasComposition] # remove spaces at begging and end
        # Check for extra species in the gasComposition input entry 
        speciesOfGasComposition = list()
        for i, sp in enumerate(gasComposition):
            speciesOfGasComposition.append(sp.split()[0])
            if speciesOfGasComposition[i] not in self._selectedReactions.keys():
                raise Exception(f'Species "{speciesOfGasComposition[i]}" does not exist in selectedReactions. File: {self._inputFileName}')
        # Check for missing species in the gasComposition input entry 
        for sp in self._selectedReactions.keys():
            if sp not in speciesOfGasComposition:
                raise Exception(f'Species "{sp}" in not declared in selectedReactions. File: {self._inputFileName}')
        # Check for invalid mole fraction entries and write mole fractions in input file
        moleFractions = dict()
        for entry in sorted(gasComposition):
            tempList = entry.split(' ')
            sp = tempList[0]
            tempList.pop(0)
            moleFractions[sp] = tempList
            if len(moleFractions[sp]) == 1:
                moleFractions[sp][0] = float(moleFractions[sp][0])
                file.write(f'{moleFractions[sp][0]} ')
            elif len(moleFractions[sp]) == 4:
                moleFractions[sp][0] = float(moleFractions[sp][0])
                moleFractions[sp][1] = float(moleFractions[sp][1])
                moleFractions[sp][2] = int(moleFractions[sp][2])
                if moleFractions[sp][3] not in ['linear', 'quadratic', 'exponential']:
                    raise Exception(f'gasComposition grid spacing of {sp} entry must be: "linear", "quadratic" or "exponential". Found "{moleFractions[sp][3]}". File: {self._inputFileName}')
                self.__bolsigRunType += 1
                self._speciesRUN2D = sp
                file.write(f'VAR ')
            else:
                raise Exception(f'gasComposition keyword must be followed by 1 or 4 values. Found {len(moleFractions[sp])} entries for {sp}. File: {self._inputFileName}')
        file.write(f'{self.__tabs(3)}/ Gas composition fractions\n')

    def writeBolsigInput(self):
        """Generate the BOLSIG+ input file for the current case.

        The method reads the case input file, validates its control keywords,
        and writes the solver-ready deck into the case `bolsigFiles`
        directory.

        Raises:
            Exception: If any required input entry is missing or malformed.
        """

        with open(self.__bolsigInputFilePath, 'w') as file:
            file.write(f'! Comment\n')
            file.write(f'/ Comment\n\n')
            file.write(f'NOSCREEN\n\n')
            file.write(f'/ NOLOGFILE\n\n')
            file.write(f'/READCOLLISIONS can be called multiple times to read from different files\n\n')
            file.write(f'/CLEARCOLLISIONS\n\n')
            file.write(f'READCOLLISIONS\n')
            file.write(f'{os.path.basename(self._crossSectionFileName).split("/")[-1]}\t\t/ File\n')
            file.write(' '.join(sp for sp in sorted(list(self._selectedReactions.keys()))))
            file.write(f'{self.__tabs(4)}/ Species\n')
            file.write('{:d}{}/ Extrapolate: 0= No 1= Yes\n\n'.format(1, self.__tabs()))

            file.write(f'CONDITIONS\n')

            self.__writeElectricFieldInputEntries(file)

            file.write('{:g}{}/ Angular field frequency / N (m3/s)\n'.format(0, self.__tabs()))
            file.write('{:g}{}/ Cosine of E-B field angle\n'.format(0, self.__tabs()))

            # Gas temperature
            gasTemp = self._readInputFile('gasTemp')
            if len(gasTemp) > 1:
                raise Exception(f'The gas temperature entries are more than one. File: {self._inputFileName}')
            file.write('{:g}{}/ Gas temperature (K)\n'.format(float(gasTemp[0]), self.__tabs()))

            file.write('{:g}{}/ Excitation temperature (K)\n'.format(300.0, self.__tabs()))
            file.write('{:g}{}/ Transition energy (eV)\n'.format(0, self.__tabs()))
            file.write('{:g}{}/ Ionization degree\n'.format(0, self.__tabs()))

            # Gas particle density
            self._gasDensity = self._readInputFile('gasDensity')
            if len(self._gasDensity) > 1:
                raise Exception(f'The gas density entries are more than one. File: {self._inputFileName}')
            file.write('{:g}{}/ Gas particle density (1/m3)\n'.format(float(self._gasDensity[0]), self.__tabs(4)))

            file.write('{:g}{}/ Ion charge parameter\n'.format(-1, self.__tabs()))
            file.write('{:g}{}/ Ion/neutral mass ratio\n'.format(1, self.__tabs()))
            file.write('{:d}{}/ e-e momentum effects & modified Coulomb logarithm: 0=No&No; 1=Yes&No; 2=No&Yes; 3=Yes&Yes*\n'.format(0, self.__tabs()))
            file.write('{:d}{}/ Energy sharing: 1=Equal*; 2=One takes all\n'.format(1, self.__tabs()))
            file.write('{:d}{}/ Growth: 1=Temporal*; 2=Spatial; 3=Not included; 4=Grad-n expansion\n'.format(1, self.__tabs()))
            file.write('{:g}{}/ Maxwellian mean energy (eV) \n'.format(0, self.__tabs()))
            file.write('{:d}{}/ # of grid points\n'.format(100, self.__tabs()))
            file.write('{:d}{}/ Manual grid: 0=No; 1=Linear; 2=Parabolic \n'.format(0, self.__tabs()))
            file.write('{:g}{}/ Manual maximum energy (eV)\n'.format(200, self.__tabs()))
            file.write('{:g}{}/ Precision\n'.format(1e-25, self.__tabs(5)))
            file.write('{:g}{}/ Convergence\n'.format(1e-8, self.__tabs(5)))
            file.write('{:d}{}/ Maximum # of iterations\n'.format(500, self.__tabs()))

            # Gas composition
            gasComposition = self._readInputFile('gasComposition') # read whole entry of input file
            gasComposition = ' '.join(gasComposition) # make all entries a single string
            gasComposition = gasComposition.split(',') # force split using commas
            gasComposition = filter(None, gasComposition) # filter out empty elements
            gasComposition = [sp.strip() for sp in gasComposition] # remove spaces at begging and end
            # Check for extra species in the gasComposition input entry 
            speciesOfGasComposition = list()
            for i, sp in enumerate(gasComposition):
                speciesOfGasComposition.append(sp.split()[0])
                if speciesOfGasComposition[i] not in self._selectedReactions.keys():
                    raise Exception(f'Species "{speciesOfGasComposition[i]}" does not exist in selectedReactions. File: {self._inputFileName}')
            # Check for missing species in the gasComposition input entry 
            for sp in self._selectedReactions.keys():
                if sp not in speciesOfGasComposition:
                    raise Exception(f'Species "{sp}" in not declared in selectedReactions. File: {self._inputFileName}')
            # Check for invalid mole fraction entries and write mole fractions in input file
            moleFractions = dict()
            for entry in sorted(gasComposition):
                tempList = entry.split(' ')
                sp = tempList[0]
                tempList.pop(0)
                moleFractions[sp] = tempList
                if len(moleFractions[sp]) == 1:
                    moleFractions[sp][0] = float(moleFractions[sp][0])
                    file.write(f'{moleFractions[sp][0]} ')
                elif len(moleFractions[sp]) == 4:
                    moleFractions[sp][0] = float(moleFractions[sp][0])
                    moleFractions[sp][1] = float(moleFractions[sp][1])
                    moleFractions[sp][2] = int(moleFractions[sp][2])
                    if moleFractions[sp][3] not in ['linear', 'quadratic', 'exponential']:
                        raise Exception(f'gasComposition grid spacing of {sp} entry must be: "linear", "quadratic" or "exponential". Found "{moleFractions[sp][3]}". File: {self._inputFileName}')
                    self.__bolsigRunType += 1
                    self._speciesRUN2D = sp
                    file.write(f'VAR ')
                else:
                    raise Exception(f'gasComposition keyword must be followed by 1 or 4 values. Found {len(moleFractions[sp])} entries for {sp}. File: {self._inputFileName}')
            file.write(f'{self.__tabs(3)}/ Gas composition fractions\n')

            file.write('{:d}{}/ Normalize composition to unity: 0=No;\n\n'.format(1, self.__tabs()))

            self.__validatePrimarySweepEntries()

            # Select the appropriate BOLSIG+ run command.
            if self.__bolsigRunType == 0:
                file.write(f'RUN\n\n')
            elif self.__bolsigRunType == 1:
                for i, entry in enumerate(self._primarySweepEntries):
                    file.write(f'RUNSERIES\n')
                    file.write('{:d}{}/ Variable: 1=E/N; 2=Mean energy; 3=Maxwellian energy\n'.format(self._primarySweepVariable, self.__tabs()))
                    file.write('{:g} {:g}{}/ Min Max\n'.format(self._primarySweepEntries[i][0], self._primarySweepEntries[i][1], self.__tabs(5)))
                    file.write('{:d}{}/ Number\n'.format(self._primarySweepEntries[i][2], self.__tabs()))
                    for j, gridType in enumerate(['linear','quadratic','exponential']):
                        if self._primarySweepEntries[i][3] == gridType:
                            file.write(f'{j+1}{self.__tabs()}/ Type1 Type2: 1=Linear; 2=Quadratic; 3=Exponential\n\n')
            elif self.__bolsigRunType == 2:
                file.write(f'RUN2D\n')
                file.write('{:d}{}/ First variable: 1=E/N; 2=Mean energy; 3=Maxwellian energy \n'.format(self._primarySweepVariable, self.__tabs()))
                file.write('{:g} {:g} {:g} {:g}{}/ Min1 Max1 Min2 Max2\n'.format(self._primarySweepEntries[0][0], self._primarySweepEntries[0][1], moleFractions[self._speciesRUN2D][0], moleFractions[self._speciesRUN2D][1], self.__tabs(4)))
                file.write('{:d} {:d}{}/ Num1 Num2\n'.format(self._primarySweepEntries[0][2], moleFractions[self._speciesRUN2D][2], self.__tabs(5)))
                for i, gridType in enumerate(['linear','quadratic','exponential']):
                    if self._primarySweepEntries[0][3] == gridType:
                        file.write(f'{i+1} ')
                for i, gridType in enumerate(['linear','quadratic','exponential']):
                    if moleFractions[self._speciesRUN2D][3] == gridType:
                        file.write(f'{i+1} ')
                file.write(f'{self.__tabs(5)}/ Type1 Type2: 1=Linear; 2=Quadratic; 3=Exponential\n')
                file.write(f'bolsigOutRun2D.dat{self.__tabs(2)}/ Output file of RUN2D\n\n') # A secondary output file, for additional info
            else:
                raise Exception('Error with the "__bolsigRunType" variable.')

            # Configure solver output generation.
            file.write(f'SAVERESULTS\n')
            file.write(f'{self._bolsigOuputFileName}\t\t/ File\n')
            file.write('{:d}{}/ Format: 1=Run by run; 2=Combined; 3=E/N; 4=Energy; 5=SIGLO; 6=PLASIMO\n'.format(2, self.__tabs()))
            file.write('{:d}{}/ Conditions: 0=No; 1=Yes\n'.format(1, self.__tabs()))
            file.write('{:d}{}/ Transport coefficients: 0=No; 1=Yes\n'.format(1, self.__tabs()))
            file.write('{:d}{}/ Rate coefficients: 0=No; 1=Yes\n'.format(1, self.__tabs()))
            file.write('{:d}{}/ Reverse rate coefficients: 0=No; 1=Yes\n'.format(0, self.__tabs()))
            file.write('{:d}{}/ Energy loss coefficients: 0=No; 1=Yes\n'.format(0, self.__tabs()))
            file.write('{:d}{}/ Distribution function: 0=No; 1=Yes \n'.format(0, self.__tabs()))
            file.write('{:d}{}/ Skip failed runs: 0=No; 1=Yes\n'.format(0, self.__tabs()))
            file.write('{:d}{}/ Include cross sections: 0=No; 1=Yes\n\n'.format(0, self.__tabs()))

            file.write('END')

        # Optionally print the selected-reaction summary.
        boolMap = { 'True': True, 'true': True, 'TRUE': True, 'False': False}
        boolValue = boolMap.get(self._readInputFile('printScreenSelectedReactions')[0])
        if boolValue:
            self._printSelectedReactions()


    def runBolsigCode(self):
        """Execute the BOLSIG+ binary for the generated input file.

        Raises:
            Exception: If the current platform is unsupported or if the solver
            process cannot be started successfully.
        """

        # Resolve the bundled BOLSIG+ executable path.
        bolsigExecutablePath = os.path.join(os.path.dirname(__file__),'bolsigExe','bolsigminus')

        # Execute the solver on the current platform.
        try:
            if platform.system() == 'Linux':
                os.chdir(os.path.join(self._inputDirPath, self._bolsigInputDirName)) # Change direction to the case
                os.system(f'{bolsigExecutablePath} {self._bolsigInputFileName}')
            elif platform.system() == 'Windows':
                raise Exception(f'Windows OS not yet supported.')
            else:
                raise Exception(f'Current OS not supported. Available OS are: UNIX/Linux.')
        except:
            raise Exception('Problem with BOLSIG+ code execution.')


    
                
