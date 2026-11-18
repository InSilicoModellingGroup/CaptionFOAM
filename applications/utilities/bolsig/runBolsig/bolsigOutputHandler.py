"""Parsing and export utilities for processed BOLSIG+ output."""

import os
import csv

class bolsigOutputReader:
    """Read BOLSIG+ output tables and export processed coefficient data."""
    
    def __init__(self, bolsigExecutorObj):
        """Initialize the output reader from an executed BOLSIG+ case.

        Args:
            bolsigExecutorObj (bolsigExecutor): Executor instance that contains
                the case paths, selected reactions, and gas density used for
                the run.
        """

        self.moleFractionsTable = list()
        self.transportPropertiesTable = list()
        self.rateConstantsTable = list()
        self.bolsigCoeffsTable = list()
        self.bolsigCoeffsTableColumnNames = list()
        self._coeffsTableFileName = str()
        self._bolsigOuputFileName = bolsigExecutorObj._bolsigOuputFileName 
        self._inputDirPath = bolsigExecutorObj._inputDirPath 
        self._speciesWithVaryingMoleFraction = getattr(bolsigExecutorObj, "_speciesRUN2D", None)
        self._gasDensity = float(bolsigExecutorObj._gasDensity[0])
        self._selectedReactions = bolsigExecutorObj._selectedReactions

    @staticmethod
    def __isNumber(s):
        """Return whether a token can be parsed as a floating-point value.

        Args:
            s (str): Token to test.

        Returns:
            bool: `True` if `s` can be converted to `float`, otherwise `False`.
        """

        try:
            float(s)
            return True
        except ValueError:
            return False

    def __checkEndOfTable(self, line):
        """Detect the end of a numeric table in the BOLSIG+ output.

        Args:
            line (str): Line read from the output file.

        Returns:
            bool: `True` when the current table should stop being parsed.
        """

        splitLine = line.strip().split()
        if not splitLine:
            return True
        return not self.__isNumber(splitLine[0])

    def __findMoleFractions(self):
        """Extract mole-fraction metadata and column names from the output.

        Raises:
            RuntimeError: If the output file does not contain mole-fraction
            metadata.
        """

        moleFractionFound = False
        with open(self._bolsigOuputFileName, 'r') as file:
            for line in file:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'Mole' and parts[2] == 'fraction':
                    moleFractionFound = True
                    self.__moleFractionsBolsigOutputEntries['bolsigOutputHeaders'].append(parts[0])
                    self.__moleFractionsBolsigOutputEntries['Species'].append(parts[3])
                    if len(parts)==4:
                        self.__moleFractionsBolsigOutputEntries['moleFractionValue'].append(float('NaN'))
                    elif len(parts)==5:
                        self.__moleFractionsBolsigOutputEntries['moleFractionValue'].append(parts[4])
                    else:
                        raise RuntimeError(f'Error in BOLSIG+ output file. Problem with entry {parts[0]} for species {part[3]}.')
            self.bolsigCoeffsTableColumnNames.extend(self.__moleFractionsBolsigOutputEntries['Species']) 
        if not moleFractionFound:
            raise RuntimeError('No mole fractions found.')
        

    def __findReactionNames(self):
        """Extract reaction-rate column names from the output file.

        Raises:
            RuntimeError: If the rate-coefficient section is missing.
        """

        reactionNamesFound = False
        with open(self._bolsigOuputFileName, 'r') as file:
            for line in file:
                parts = line.split()
                if parts and parts[0] == 'Rate':
                    reactionNamesFound = True
                    for line in file:
                        parts = line.split()
                        if parts and parts[0] == 'R#':
                            break
                        self.bolsigCoeffsTableColumnNames.append(parts[0])
        if not reactionNamesFound:
            raise RuntimeError('No reactions found.')
        
    def __findReducedElectricField(self):
        """Read the fixed reduced electric field from a single-run output.

        Returns:
            float: Reduced electric field in Townsend.

        Raises:
            RuntimeError: If the electric-field value cannot be located or
            parsed from the output file.
        """

        with open(self._bolsigOuputFileName, 'r') as file:
            for line in file:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == 'Electric' and parts[2] == 'field':
                    for token in reversed(parts):
                        if self.__isNumber(token):
                            return float(token)
                    raise RuntimeError('Electric field entry found, but no numeric value was detected.')
        raise RuntimeError('Reduced electric field not found in BOLSIG+ output.')

    def __readTabularData(self, file, table):
        """Read numeric rows from the current table section.

        Args:
            file: Open file handle positioned at the first data row.
            table (list): Destination list that receives parsed numeric rows.
        """

        for line in file:
            if self.__checkEndOfTable(line):
                break
            row = [float(x) for x in line.split() if self.__isNumber(x)]
            if row:
                table.append(row)

    def processFile(self):
        """Parse the BOLSIG+ output file into combined coefficient tables.

        Raises:
            FileNotFoundError: If the expected BOLSIG+ output file does not
            exist.
            RuntimeError: If the output layout is incompatible with the
            expected BOLSIG+ format.
        """

        # Initialize the metadata extracted from the mole-fraction header block.
        self.__moleFractionsBolsigOutputEntries = dict()
        self.__moleFractionsBolsigOutputEntries['Species'] = list()
        self.__moleFractionsBolsigOutputEntries['bolsigOutputHeaders'] = list()
        self.__moleFractionsBolsigOutputEntries['moleFractionValue'] = list()

        # Confirm that the expected solver output file is present.
        if not os.path.isfile(self._bolsigOuputFileName):
            raise FileNotFoundError('File not found')

        # Initialize the combined coefficient-table column names.
        if not self.bolsigCoeffsTableColumnNames:
            self.bolsigCoeffsTableColumnNames.append('E/N_(Td)')
            self.__findMoleFractions()
            self.bolsigCoeffsTableColumnNames.extend(['MeanEnergy_(eV)', 'Mobility*N_((1/m/V/s))', 'Diffusivity*N_(1/m/s)', 'energyMobility*N_(1/m/V/s)', 'energyDiffusivity*N_(1/m/s)', 'powerLoss/N_(eVm3/s)'])
            self.__findReactionNames()
        else:
            raise RuntimeError('Error when initializing bolsigCoeffsTableColumnNames vector. Vector was not initially empty.')

        # Parse the tabulated sections in the solver output file.
        with open(self._bolsigOuputFileName, 'r') as file:
            count = 0
            for line in file:
                line = line.strip()

                # Each `R#` line marks the start of a new table section.
                if line.startswith('R#'):
                    count += 1

                    # Read the run conditions and composition table.
                    if count == 1:
                        self.__readTabularData(file, self.moleFractionsTable) 
                        headerList = line.split() # Get the headers of the first table
                        headerList.pop(0) # Delete the "R#" entry for run number
                        varyingHeaders = headerList[1:] if headerList else list()

                        # A single `RUN` contains no varying headers in the
                        # first table, so the fixed E/N value must be read
                        # from the conditions block instead.
                        if not headerList:
                            self.bolsigCoeffsTable.append([self.__findReducedElectricField()])
                            self.bolsigCoeffsTable[0].extend(self.__moleFractionsBolsigOutputEntries['moleFractionValue'])
                        elif set(varyingHeaders) == set(self.__moleFractionsBolsigOutputEntries['bolsigOutputHeaders']):
                            for row in self.moleFractionsTable:
                                self.bolsigCoeffsTable.append(row[1:])
                        else:
                            for i, row in enumerate(self.moleFractionsTable):
                                self.bolsigCoeffsTable.append(row[1:2])
                                self.bolsigCoeffsTable[i].extend(self.__moleFractionsBolsigOutputEntries['moleFractionValue'])

                    # Read the transport and energy-loss coefficients.
                    elif count == 2:
                        summed = [0.0]*5
                        self.__readTabularData(file, self.transportPropertiesTable)
                        for i, row in enumerate(self.transportPropertiesTable):
                            self.bolsigCoeffsTable[i].extend(row[2:7])
                            summed_12_14 = sum(float(x) for x in (row[12], row[13], row[14]))
                            self.bolsigCoeffsTable[i].append(summed_12_14)

                    # Read the reaction-rate coefficients.
                    elif count == 3:
                        self.__readTabularData(file, self.rateConstantsTable)
                        for i, row in enumerate(self.rateConstantsTable):
                            self.bolsigCoeffsTable[i].extend(row[3:])
                        break

    @staticmethod
    def printTable(table):
        """Print a numeric table row-by-row.

        Args:
            table (list): Table data to print.
        """

        for row in table:
            print(' '.join(map(str, row)))



    def writeResults(self, fileFormat, filename):
        """
        Write the processed BOLSIG+ coefficients to a file.

        Args:
            fileFormat (str): Output format. Supported values are `"csv"`,
                `"dat"`, and `"openfoam"`.
            filename (str): Base name of the output file.

        Raises:
            ValueError: If `fileFormat` is not one of the supported export
            formats.
        """

        self._coeffsTableFileName = filename

        # Create the output directory for processed results.
        self._bolsigOuputDirName = os.path.join(self._inputDirPath, 'bolsigOutput')
        os.makedirs(self._bolsigOuputDirName, exist_ok=True)

        # Dispatch to the requested writer implementation.
        writers = {
            "csv": self._writeCsv,
            "dat": self._writeDat,
            "openfoam": self._writeOpenFoamDict
        }

        if fileFormat not in writers:
            raise ValueError('File format must be "csv", "dat", or "openfoam".')

        writers[fileFormat]()


    def _writeCsv(self):
        """
        Write the processed coefficient table to a CSV file.
        """
        path = os.path.join(self._bolsigOuputDirName, self._coeffsTableFileName + '.csv')

        with open(path, mode='w', newline='') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerow(self.bolsigCoeffsTableColumnNames)
            writer.writerows(self.bolsigCoeffsTable)
        print(f'Data written to {path}')


    def _writeDat(self):
        """
        Write the processed coefficient table to a fixed-width `.dat` file.
        """
        path = os.path.join(self._bolsigOuputDirName, self._coeffsTableFileName + '.dat')

        with open(path, mode='w') as file:
            header_line = ''.join(f"{col:>26}" for col in self.bolsigCoeffsTableColumnNames)
            file.write(header_line + '\n')

            for row in self.bolsigCoeffsTable:
                line = ''.join(f"{float(val):26.10e}" for val in row)
                file.write(line + '\n')

        print(f'Data written to {path}')


    def _writeOpenFoamDict(self):
        """
        Write the processed coefficient table to an OpenFOAM dictionary file.
        """
        path = os.path.join(self._bolsigOuputDirName, self._coeffsTableFileName)

        with open(path, mode='w') as file:
            file.write(r'/*--------------------------------*- C++ -*----------------------------------*\ ' + '\n')
            file.write(r'| =========                 |                                                 |' + '\n')
            file.write(r'| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |' + '\n')
            file.write(r'|  \\    /   O peration     | Version:  2406                                  |' + '\n')
            file.write(r'|   \\  /    A nd           | Website:  www.openfoam.com                      |' + '\n')
            file.write(r'|    \\/     M anipulation  |                                                 |' + '\n')
            file.write(r'\*---------------------------------------------------------------------------*/' + '\n')
            file.write(r'FoamFile' + '\n')
            file.write(r'{' + '\n')
            file.write(r'    version     2.0;' + '\n')
            file.write(r'    format      ascii;' + '\n')
            file.write(r'    class       dictionary;' + '\n')
            file.write(r'    object      bolsigProperties;' + '\n')
            file.write(r'}' + '\n')
            file.write(r'// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //' + '\n\n')

            self.__writeEN(file)

            self.__writeNumberDensity(file)

            self.__writeMeanEnergy(file, 'MeanEnergy_(eV)', 'meanEnergy')
            self.__writeTransportCoefficient(file, 'Mobility*N_((1/m/V/s))', 'electronMobility')
            self.__writeTransportCoefficient(file, 'Diffusivity*N_(1/m/s)', 'electronDiffusivity')
            self.__writeTransportCoefficient(file, 'energyMobility*N_(1/m/V/s)', 'energyMobility')
            self.__writeTransportCoefficient(file, 'energyDiffusivity*N_(1/m/s)', 'energyDiffusivity')
            self.__writePowerLoss(file, 'powerLoss/N_(eVm3/s)', 'powerLoss')

            self.__writeReactionRateCoefficients(file)


    def __writeEN(self, file):
        """
        Write the unique reduced-electric-field values to the OpenFOAM output.

        Args:
            file: Open file handle for the OpenFOAM dictionary.
        """
        # Collect unique E/N values in their original order.
        uniqueVlues = set()
        EN = list()
        for row in self.bolsigCoeffsTable:
            val = float(row[0])
            if val not in uniqueVlues:
                uniqueVlues.add(val)
                EN.append(val)

        if len(EN) > 1:
            file.write('EN\n(\n')
            for val in EN:
                file.write(f'    {val:.6f}\n')
            file.write(');\n\n')


    def __writeNumberDensity(self, file):
        """
        Write the varying-species values to the OpenFOAM dictionary.

        Args:
            file: Open file handle for the OpenFOAM dictionary.
        """
        species = self._speciesWithVaryingMoleFraction

        if not species:
            return  # No varying species defined; nothing to write

        if species not in self.bolsigCoeffsTableColumnNames:
            raise ValueError(f"Species '{species}' not found in BOLSIG+ output.")

        index = self.bolsigCoeffsTableColumnNames.index(species)

        # Collect unique mole-fraction values in their original order.
        uniqueValues = set()
        moleFractions = list()
        for row in self.bolsigCoeffsTable:
            val = float(row[index])
            if val not in uniqueValues:
                uniqueValues.add(val)
                moleFractions.append(val)

        if len(moleFractions) > 1:
            file.write(f"{species}\n(\n")
            for val in moleFractions:
                file.write(f"    {val:.6f}\n")
            file.write(");\n\n")


    def __writeTransportCoefficient(self, file, coeffNameBolsig, coeffNameOpenFoam):
        """
        Write one transport-coefficient field to the OpenFOAM dictionary.

        Args:
            file: Open file handle for the OpenFOAM dictionary.
            coeffNameBolsig (str): Column name in the processed BOLSIG+ table.
            coeffNameOpenFoam (str): Field name written to the OpenFOAM
                dictionary.
        """

        index = self.bolsigCoeffsTableColumnNames.index(coeffNameBolsig)

        # Convert BOLSIG+ values from coefficient-times-density to coefficients.
        transpCoeff = list()
        for row in self.bolsigCoeffsTable:
            val = float(row[index]/self._gasDensity)
            transpCoeff.append(val)

        if len(transpCoeff) > 1:
            file.write(f'{coeffNameOpenFoam}\n(\n')
            for val in transpCoeff:
                file.write(f'    {val:.6e}\n')
            file.write(');\n\n')
            
    def __writeMeanEnergy(self, file, coeffNameBolsig, coeffNameOpenFoam):
        """
        Write the mean-energy field to the OpenFOAM dictionary.

        Args:
            file: Open file handle for the OpenFOAM dictionary.
            coeffNameBolsig (str): Column name in the processed BOLSIG+ table.
            coeffNameOpenFoam (str): Field name written to the OpenFOAM
                dictionary.
        """

        index = self.bolsigCoeffsTableColumnNames.index(coeffNameBolsig)

        # Copy the mean-energy values into OpenFOAM dictionary format.
        transpCoeff = list()
        for row in self.bolsigCoeffsTable:
            val = float(row[index])
            transpCoeff.append(val)

        if len(transpCoeff) > 1:
            file.write(f'{coeffNameOpenFoam}\n(\n')
            for val in transpCoeff:
                file.write(f'    {val:.6e}\n')
            file.write(');\n\n')

    def __writePowerLoss(self, file, coeffNameBolsig, coeffNameOpenFoam):
        """
        Write the power-loss field to the OpenFOAM dictionary.

        Args:
            file: Open file handle for the OpenFOAM dictionary.
            coeffNameBolsig (str): Column name in the processed BOLSIG+ table.
            coeffNameOpenFoam (str): Field name written to the OpenFOAM
                dictionary.
        """

        index = self.bolsigCoeffsTableColumnNames.index(coeffNameBolsig)

        # Convert BOLSIG+ power loss from eV*m3/s to J/s.
        powerLoss = list()
        for row in self.bolsigCoeffsTable:
            val = float(row[index]*self._gasDensity * 1.602176634e-19)  # Convert eV*m3/s to J/s
            powerLoss.append(val)

        if len(powerLoss) > 1:
            file.write(f'{coeffNameOpenFoam}\n(\n')
            for val in powerLoss:
                file.write(f'    {val:.6e}\n')
            file.write(');\n\n')


    def __writeReactionRateCoefficients(self, file):
        """
        Write the reaction rate constants to the OpenFOAM dictionary.

        Args:
            file: Open file handle for the OpenFOAM dictionary.

        Raises:
            RuntimeError: If the processed table does not contain reaction-rate
            columns.
        """
        try:
            index = self.bolsigCoeffsTableColumnNames.index('C1')
        except ValueError:
            raise RuntimeError("Column 'C1' not found. Reaction rate coefficients are missing.")
        
        # Exclude elastic and effective collisions from the exported list.
        count = 0
        excludeTableHeads = list()
        for sp in self._selectedReactions:
            for r, react in enumerate(self._selectedReactions[sp]["reaction"]):
                if self._selectedReactions[sp]["reaction"][r].split()[-1].strip() in ["Elastic", "Effective"]:
                    excludeTableHeads.append(count)
                count += 1

        for i, entry in enumerate(excludeTableHeads):
            excludeTableHeads[i] = entry + index

        indices = list()
        for i in range(index, len(self.bolsigCoeffsTableColumnNames)):
            if i<index:
                continue
            if i not in excludeTableHeads:
                indices.append(i)

        file.write('rateCoefficients\n(\n')
        for row in self.bolsigCoeffsTable:
            coeffs = [row[i] for i in indices]
            formatted = ' '.join(f'{float(c):.6e}' for c in coeffs)
            file.write(f'    ({formatted})\n')
        file.write(');\n\n')
