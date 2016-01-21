# -*- coding: utf-8 -*-


# FuzzyClassificator - this program uses neural networks to solve classification problems,
# and uses fuzzy sets and fuzzy logic to interpreting results.
# Copyright (C) 2014, Timur Gilmullin
# e-mail: tim55667757@gmail.com


# License: GNU GPL v3

# This file is part of FuzzyClassificator program.

# FuzzyClassificator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# FuzzyClassificator program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Foobar.
# If not, see <http://www.gnu.org/licenses/>.

# Этот файл - часть программы FuzzyClassificator.

# FuzzyClassificator - свободная программа: вы можете перераспространять ее и/или
# изменять ее на условиях Стандартной общественной лицензии GNU в том виде,
# в каком она была опубликована Фондом свободного программного обеспечения;
# либо версии 3 лицензии, либо (по вашему выбору) любой более поздней версии.

# Программа FuzzyClassificator распространяется в надежде, что она будет полезной,
# но БЕЗО ВСЯКИХ ГАРАНТИЙ; даже без неявной гарантии ТОВАРНОГО ВИДА
# или ПРИГОДНОСТИ ДЛЯ ОПРЕДЕЛЕННЫХ ЦЕЛЕЙ.
# Подробнее см. в Стандартной общественной лицензии GNU.

# Вы должны были получить копию Стандартной общественной лицензии GNU
# вместе с этой программой. Если это не так, см. <http://www.gnu.org/licenses/>.)


# Library for work with fuzzy neural networks.


import csv
import os
import shutil
from datetime import datetime

from pybrain.tools.shortcuts import buildNetwork
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.tools.customxml.networkwriter import NetworkWriter
from pybrain.tools.customxml.networkreader import NetworkReader

from FuzzyRoutines import *
from FCLogger import FCLogger


class FuzzyNeuroNetwork(object):
    """
    Methods for work with raw-data and fuzzy neural networks.
    """

    def __init__(self):
        self.scale = UniversalFuzzyScale()  # creating fuzzy scale S_f = {Min, Low, Med, High, Max}

        self.networkFile = ''  # file with PyBrain network xml-configuration
        self.rawDataFile = ''  # file with text raw-data for learning
        self.reportFile = ''  # filename for report with classification analysis
        self.bestNetworkFile = ''  # best network
        self.bestNetworkInfoFile = ''  # information about best network

        self.config = ()  # network configuration is a tuple of numbers: (inputs_dim, layer1_dim,..., layerN_dim, outputs_dim)

        self._rawData = []  # list of raw strings data without 1st header line: ['input_vector',  'output_vector']
        self.headers = []  # list of strings with parsed headers. 1st line always use as header line.
        self._rawDefuzData = []  # list of raw strings data but with deffazification values if it present in self._rawData

        self.dataSet = None  # PyBrain-formatted dataset after parsing raw-data: [[input_vector], [output_vector]]
        self.network = None  # PyBrain neural network instance
        self.trainer = None  # PyBrain trainer instance

        self._epochs = 10  # Epochs of learning
        self._learningRate = 0.05  # Learning rate
        self._momentum = 0.01  # Momentum of learning
        self._epsilon = 0.01  # Used to compare the distance between the two vectors if self._stop > 0.
        self._stop = 0  # Stop if errors count on ethalon vectors less than this number of percents during the traning. If 0 then used only self._epochs value.

        self._epochsToUpdate = 5  # epochs between error status updated
        self.currentFalsePercent = 100.0  # current percents of false classificated vectors
        self.bestNetworkFalsePercent = self.currentFalsePercent  # best network with minimum percents of false classificated vectors

        self._ignoreColumns = []  # List of indexes of ignored columns. Start from 0: 1st column encode as index 0.
        self._ignoreRows = [0]  # List of indexes of ignored rows. 1st line with headers always ignored. Start from 0: 1st line encode as index 0.
        self._separator = '\t'  # Tab symbol used as separator by default

    def DefuzRawData(self):
        """
        Functions parse raw text data and converting fuzzy values to its real represents.
        """
        FCLogger.info('Defuzzyficating raw data ...')
        defuzData = []

        try:
            for line in self.rawData:
                # defuzzificating fuzzy values to real values:
                defuzzyValues = []

                for itemValue in line:
                    num = 0
                    try:
                        num = float(itemValue)

                    except:
                        level = self.scale.GetLevelByName(levelName=itemValue, exactMatching=False)

                        if level:
                            num = level['fSet'].Defuz()

                        else:
                            FCLogger.warning('{} not correct real or fuzzy value! It is reset at 0.'.format(itemValue))

                    defuzzyValues.append(num)

                defuzData.append(defuzzyValues)

        except:
            defuzData = []
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while defuzzyficating values in raw data!')

        finally:
            self._rawDefuzData = defuzData

    @property
    def rawData(self):
        return self._rawData

    @rawData.setter
    def rawData(self, value):
        if isinstance(value, list):
            self._rawData = value

        else:
            self._rawData = []
            FCLogger.warning('Raw text data might be a list of strings! It was set to empty list: [].')

    @property
    def rawDefuzData(self):
        return self._rawDefuzData

    @property
    def epochs(self):
        return self._epochs

    @epochs.setter
    def epochs(self, value):
        if isinstance(value, int):

            if value >= 0:
                self._epochs = value

            else:
                self._epochs = 1
                FCLogger.warning('Parameter epochs might be greater or equal 0! It was set to 1.')

        else:
            self._epochs = 10
            FCLogger.warning('Parameter epochs might be an integer number! It was set to 10, by default.')

    @property
    def learningRate(self):
        return self._learningRate

    @learningRate.setter
    def learningRate(self, value):
        if isinstance(value, float):

            if (value > 0) and (value <= 1):
                self._learningRate = value

            elif value <= 0:
                self._learningRate = 0.05
                FCLogger.warning('Parameter rate might be greater than 0! It was set to 0.05 now.')

            else:
                self._learningRate = 1
                FCLogger.warning('Parameter rate might be less or equal 1! It was set to 1 now.')

        else:
            self._learningRate = 0.05
            FCLogger.warning('Parameter rate might be a float number! It was set to 0.05, by default.')

    @property
    def momentum(self):
        return self._momentum

    @momentum.setter
    def momentum(self, value):
        if isinstance(value, float):

            if (value > 0) and (value <= 1):
                self._momentum = value

            elif value <= 0:
                self._momentum = 0.01
                FCLogger.warning('Parameter momentum might be greater than 0! It was set to 0.01 now.')

            else:
                self._momentum = 1
                FCLogger.warning('Parameter momentum might be less or equal 1! It was set to 1 now.')

        else:
            self._momentum = 0.01
            FCLogger.warning('Parameter momentum might be a float number! It was set to 0.01, by default.')

    @property
    def epsilon(self):
        return self._epsilon

    @epsilon.setter
    def epsilon(self, value):
        if isinstance(value, float):

            if (value > 0) and (value <= 1):
                self._epsilon = value

            elif value <= 0:
                self._epsilon = 0.01
                FCLogger.warning('Parameter epsilon might be greater than 0! It was set to 0.01 now.')

            else:
                self._epsilon = 1
                FCLogger.warning('Parameter epsilon might be less or equal 1! It was set to 1 now.')

        else:
            self._epsilon = 0.01
            FCLogger.warning('Parameter epsilon might be a float number! It was set to 0.01, by default.')

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, value):
        if isinstance(value, float):

            if (value >= 0) and (value <= 100):
                self._stop = value

            else:
                self._stop = 0
                FCLogger.warning('Parameter stop might be greater than 0 and less or equal 100! It was set to 0 now.')

        else:
            self._stop = 0
            FCLogger.warning('Parameter stop might be a float number! It was set to 0, by default.')

    @property
    def epochsToUpdate(self):
        return self._epochsToUpdate

    @epochsToUpdate.setter
    def epochsToUpdate(self, value):
        if isinstance(value, int):

            if value >= 1:
                self._epochsToUpdate = value

            else:
                self._epochsToUpdate = 1
                FCLogger.warning('Parameter epochsToUpdate might be greater or equal 1! It was set to 1.')

        else:
            self._epochsToUpdate = 5
            FCLogger.warning('Parameter epochs might be an integer number! It was set to 5, by default.')

    @property
    def ignoreColumns(self):
        return self._ignoreColumns

    @ignoreColumns.setter
    def ignoreColumns(self, value):
        if isinstance(value, list):
            self._ignoreColumns = []

            for el in value:
                if not isinstance(el, int):
                    self._ignoreColumns = []
                    FCLogger.warning('Parameter ignoreColumns must be list of numbers! It was set to empty list, by default.')
                    break

                else:
                    if el > 0:
                        self._ignoreColumns.append(el - 1)
                        FCLogger.debug('Column added to ignore list: {} (index: {})'.format(el, el - 1))

                    else:
                        FCLogger.debug('Column {} (index: {}) not added to ignoreColumns list.'.format(el, el - 1))

        else:
            self._ignoreColumns = []
            FCLogger.warning('Parameter ignoreColumns must be list of numbers! It was set to empty list, by default.')

        self._ignoreColumns = list(set(self._ignoreColumns))

    @property
    def ignoreRows(self):
        return self._ignoreRows

    @ignoreRows.setter
    def ignoreRows(self, value):
        if isinstance(value, list):
            self._ignoreRows = [0]  # always ignore 1st header line

            for el in value:
                if not isinstance(el, int):
                    self._ignoreRows = [0]
                    FCLogger.warning('Parameter ignoreRows must be list of numbers! It was set to [0], by default.')
                    break

                else:
                    if el > 0:
                        self._ignoreRows.append(el - 1)
                        FCLogger.debug('Row added to ignore list: {} (index: {})'.format(el, el - 1))

                    else:
                        FCLogger.debug('Row {} (index: {}) not added to ignoreRows list.'.format(el, el - 1))

        else:
            self._ignoreRows = [0]
            FCLogger.warning('Parameter ignoreRows must be list of numbers! It was set to [0], by default.')

        self._ignoreRows = list(set(self._ignoreRows))

    @property
    def separator(self):
        return self._separator

    @separator.setter
    def separator(self, value):
        if isinstance(value, str):

            if value.upper() == 'TAB':
                self._separator = '\t'

            elif value.upper() == 'SPACE':
                self._separator = ' '

            else:
                if len(value) == 1:
                    self._separator = value

                else:
                    FCLogger.warning('Parameter separator must be an 1-character string! It was set to TAB char, by default.')
                    self._separator = '\t'

        else:
            self._separator = '\t'
            FCLogger.warning('Parameter separator must be an 1-character string! It was set to TAB char, by default.')

    def ParseRawDataFile(self):
        """
        Get list of lines with raw string data without first header-line and empty lines.
        """
        FCLogger.info('Parsing file with raw data...')

        raw = []

        try:
            if self.rawDataFile:
                with open(self.rawDataFile, newline='') as csvfile:
                    FCLogger.debug('Opened file: {}'.format(self.rawDataFile))
                    FCLogger.debug('Separator symbol used: {}'.format('TAB' if self.separator == '\t' else '{}'.format('SPACE' if self.separator == ' ' else self.separator)))
                    FCLogger.debug('Ignored row indexes (1st row is 0): {}'.format(self.ignoreRows))
                    FCLogger.debug('Ignored column indexes (1st column is 0): {}'.format(self.ignoreColumns))

                    for row in csv.reader(csvfile, delimiter=self._separator):
                        if row:
                            raw.append(row)

                if raw:
                    newRaw = []  # removing ignored rows and columns:
                    for indexRow, row in enumerate(raw):
                        if indexRow not in self._ignoreRows or indexRow == 0:
                            newline = []

                            for indexCol, col in enumerate(row):
                                if indexCol not in self._ignoreColumns:
                                    newline.append(col)

                            newRaw.append(newline)

                    self.headers = newRaw[0]  # header-line is always 1st line in input file
                    raw = newRaw[1:]  # cut headers

                    FCLogger.debug('Parsed raw-data (without ignored rows and columns):')

                    if len(raw) <= 10:
                        for line in raw:
                            if len(line) <= 10:
                                FCLogger.debug('    {}'.format(line))

                            else:
                                FCLogger.debug('    [{}, {}, ..., {}, {}]'.format(line[0], line[1], line[-2], line[-1]))

                    else:
                        FCLogger.debug('    {}'.format(raw[0] if len(raw[0]) <= 10 else '[{}, {}, ..., {}, {}]'.format(raw[0][0], raw[0][1], raw[0][-2], raw[0][-1])))
                        FCLogger.debug('    {}'.format(raw[0] if len(raw[1]) <= 10 else '[{}, {}, ..., {}, {}]'.format(raw[1][0], raw[1][1], raw[1][-2], raw[1][-1])))
                        FCLogger.debug('    [ ... skipped ... ]')
                        FCLogger.debug('    {}'.format(raw[0] if len(raw[0]) <= 10 else '[{}, {}, ..., {}, {}]'.format(raw[-2][0], raw[-2][1], raw[-2][-2], raw[-2][-1])))
                        FCLogger.debug('    {}'.format(raw[0] if len(raw[0]) <= 10 else '[{}, {}, ..., {}, {}]'.format(raw[-1][0], raw[-1][1], raw[-1][-2], raw[-1][-1])))

                FCLogger.info('File with raw data successfully parsed.')

            else:
                FCLogger.warning('File with raw data not define or not exist!')

        except:
            raw = []
            self.headers = []
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while parsing raw data file!')

        finally:
            if not raw:
                FCLogger.warning('Empty raw data file!')

            self.rawData = raw  # list of input vectors without first header line
            self.DefuzRawData()  # defuzzificating raw data

    def PrepareDataSet(self):
        """
        This method preparing PyBrain dataset from raw data file.
        """
        FCLogger.info('Converting parsed and defuzzificated raw-data into PyBrain dataset format...')

        learnData = None

        try:
            if self.config:

                if len(self.config) > 2:
                    learnData = SupervisedDataSet(self.config[0], self.config[-1])  # first and last values in config tuple

                else:
                    raise Exception('Network config must contains more than 2 parameters!')

            else:
                raise Exception('Network config not defined!')

            # add samples from defuz raw-data as [[input_vector], [output_vector]] for PyBrain network:
            for sample in self._rawDefuzData:
                learnData.addSample(sample[:self.config[0]], sample[self.config[0]:self.config[0] + self.config[-1]])

            FCLogger.debug('PyBrain dataset vectors, inputs and outputs (targets):')

            allInputs = learnData.data['input'][:learnData.endmarker['input']]
            learnDataInputsString = str(allInputs).split('\n')
            FCLogger.debug("- input vectors, dim({}, {}):".format(len(allInputs[0]), len(allInputs)))

            if len(allInputs) <= 10:
                for value in learnDataInputsString:
                    FCLogger.debug('    {}'.format(value))

            else:
                FCLogger.debug('    {}'.format(learnDataInputsString[0]))
                FCLogger.debug('    {}'.format(learnDataInputsString[1]))
                FCLogger.debug('     [ ... skipped ... ]')
                FCLogger.debug('    {}'.format(learnDataInputsString[-2]))
                FCLogger.debug('    {}'.format(learnDataInputsString[-1]))

            allTargets = learnData.data['target'][:learnData.endmarker['target']]
            learnDataTargetsString = str(allTargets).split('\n')
            FCLogger.debug("- output vectors, dim({}, {}):".format(len(allTargets[0]), len(allTargets)))

            if len(allTargets) <= 10:
                for value in learnDataTargetsString:
                    FCLogger.debug('    {}'.format(value))

            else:
                FCLogger.debug('    {}'.format(learnDataTargetsString[0]))
                FCLogger.debug('    {}'.format(learnDataTargetsString[1]))
                FCLogger.debug('     [ ... skipped ... ]')
                FCLogger.debug('    {}'.format(learnDataTargetsString[-2]))
                FCLogger.debug('    {}'.format(learnDataTargetsString[-1]))

            FCLogger.info('PyBrain dataset successfully prepared.')

        except:
            learnData = None
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while preparing PyBrain dataset! Check your configuration parameters!')

        finally:
            self.dataSet = learnData

    def CreateNetwork(self):
        """
        This method creating instance of PyBrain network.
        """
        FCLogger.info('Creating PyBrain network...')

        net = None

        try:
            if self.config:

                if len(self.config) > 2:
                    hLayers = self.config[1:-1]  # parameters for hidden layers

                    FCLogger.info('Neuronet configuration: Config = <inputs, {layers}, outputs>')
                    FCLogger.info('    - inputs is dimension of all input vectors: {},'.format(self.config[0]))
                    FCLogger.info('    - outputs is dimension of all output vectors: {},'.format(self.config[-1]))
                    FCLogger.info('    - count of hidden layers for Neuronet: {},'.format(len(hLayers)))

                    if len(hLayers) <= 10:
                        for nNum, dim in enumerate(hLayers):
                            FCLogger.info('      ... dimension of {} hidden layer: {}'.format(nNum, dim))

                    else:
                        FCLogger.info('      ... dimension of 0 hidden layer: {}'.format(hLayers[0]))
                        FCLogger.info('      ... dimension of 1 hidden layer: {}'.format(hLayers[1]))
                        FCLogger.info('      ... skipped ...')
                        FCLogger.info('      ... dimension of {} hidden layer: {}'.format(len(hLayers) - 2, hLayers[-2]))
                        FCLogger.info('      ... dimension of {} hidden layer: {}'.format(len(hLayers) - 1, hLayers[-1]))

                    net = buildNetwork(*self.config)  # create network with config

                else:
                    raise Exception('Network config must contains at least 3 parameters: (inputs_count, layer1_count, outputs_count)!')

            else:
                raise Exception('Network config not defined!')

            FCLogger.info('PyBrain network successfully created.')

        except:
            net = None
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while preparing PyBrain network!')

        finally:
            self.network = net

    def CreateTrainer(self):
        """
        This method preparing PyBrain trainer.
        """
        FCLogger.info('Initializing PyBrain backpropagating trainer...')

        backpropTrainer = None

        try:
            if self.network:

                if self.dataSet:
                    FCLogger.info('Trainer using parameters:')
                    FCLogger.info('    - PyBrain network previously created,')
                    FCLogger.info('    - PyBrain dataset previously created,')
                    FCLogger.info('    - epoch parameter: {}'.format(self._epochs))
                    FCLogger.info('    - network learning rate parameter: {}'.format(self._learningRate))
                    FCLogger.info('    - momentum parameter: {}'.format(self._momentum))
                    FCLogger.info('    - epsilon parameter: {}'.format(self._epsilon))
                    FCLogger.info('    - stop parameter: {:.1f}%'.format(self._stop))

                    backpropTrainer = BackpropTrainer(self.network, self.dataSet, learningrate=self._learningRate, momentum=self._momentum)

                else:
                    raise Exception('PyBrain dataset not exist!')

            else:
                raise Exception('PyBrain network not exist!')

            FCLogger.info('PyBrain network successfully created.')

        except:
            backpropTrainer = None
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while creating PyBrain trainer!')

        finally:
            self.trainer = backpropTrainer

    def SaveNetwork(self):
        """
        Creating dump of network.
        """
        FCLogger.debug('Autosaving - enabled. Trying to save network as PyBrain xml-formatted file...')

        NetworkWriter.writeToFile(self.network, self.networkFile)

        FCLogger.info('Current network saved to file: {}'.format(os.path.abspath(self.networkFile)))

    def LoadNetwork(self):
        """
        Loading network dump from file.
        """
        FCLogger.debug('Loading network from PyBrain xml-formatted file...')

        net = None

        if os.path.exists(self.networkFile):
            net = NetworkReader.readFrom(self.networkFile)

            FCLogger.info('Network loaded from dump-file: {}'.format(os.path.abspath(self.networkFile)))

        else:
            FCLogger.warning('{} - file with Neural Network configuration not exist!'.format(os.path.abspath(self.networkFile)))

        self.network = net

    def ClassificationResultForOneVector(self, inputVector, expectedVector=None, needFuzzy=False):
        """
        Method use for receiving results after activating Neuronet with one input vector.
        inputVector - is a defuzzyficated raw data of input vector.
        If needFuzzy = True then appropriate output values converting into fuzzy values after activating, otherwise used real values.
        """
        defuzInput = []

        # defuzzyficating input values:
        for value in inputVector:
            level = self.scale.GetLevelByName(levelName='{}'.format(value), exactMatching=False)

            if level:
                defuzInput.append(level['fSet'].Defuz())

            else:
                defuzInput.append(value)

        outputVector = self.network.activate(defuzInput)

        defuzExpectedVector = []

        # defuzzyficate expected values:
        if expectedVector:
            for value in expectedVector:
                level = self.scale.GetLevelByName(levelName='{}'.format(value), exactMatching=False)

                if level:
                    defuzExpectedVector.append(level['fSet'].Defuz())

                else:
                    defuzExpectedVector.append(value)

            errorVector = []

            for num, currentValue in enumerate(outputVector):
                errorVector.append(float(defuzExpectedVector[num]) - currentValue)

        else:
            errorVector = None

        if needFuzzy:
            fuzzyOutputVector = []

            for value in outputVector:
                fuzzyOutputVector.append(self.scale.Fuzzy(value)['name'])

            if len(inputVector) <= 10:
                FCLogger.debug('        Input: {}\tOutput: {}{}'.format(inputVector, fuzzyOutputVector, '\tExpected: {}'.format(expectedVector) if expectedVector else ''))

            else:
                cutInput = '[{}, {}, ..., {}, {}]'.format(inputVector[0], inputVector[1], inputVector[-2], inputVector[-1])
                FCLogger.debug('        Input: {}\tOutput: {}{}'.format(cutInput, fuzzyOutputVector, '\tExpected: {}'.format(expectedVector) if expectedVector else ''))

            return inputVector, fuzzyOutputVector, expectedVector, errorVector

        else:
            if len(defuzInput) <= 10:
                FCLogger.debug('        Input: {}\tOutput: {}{}'.format(defuzInput, outputVector, '\tExpected: {}'.format(defuzExpectedVector) if expectedVector and defuzExpectedVector and errorVector else ''))

            else:
                cutDefuzInput = '[{}, {}, ..., {}, {}]'.format(defuzInput[0], defuzInput[1], defuzInput[-2], defuzInput[-1])
                FCLogger.debug('        Input: {}\tOutput: {}{}'.format(cutDefuzInput, outputVector, '\tExpected: {}'.format(defuzExpectedVector) if expectedVector and defuzExpectedVector and errorVector else ''))

            if expectedVector and defuzExpectedVector and errorVector:
                FCLogger.debug('        Error: {}'.format(errorVector))

            return defuzInput, outputVector, defuzExpectedVector, errorVector

    def ClassificationResults(self, fullEval=False, needFuzzy=False, showExpectedVector=True):
        """
        Method use for receiving results after activating Neuronet with all input vectors.
        If fullEval = True then method calculate results for all input vectors, otherwise for first and last two input vectors.
        If needFuzzy = True then appropriate output values converting into fuzzy values after activating, otherwise used real values.
        If showExpectedVector = True then vector with expected results will shown in log and result file.
        """
        classificationResults = []

        inputHeaders = self.headers[:self.config[0]]
        outputHeaders = self.headers[len(self.headers) - self.config[-1]:]

        if fullEval:
            FCLogger.debug('Full classification results:')

            if len(inputHeaders) <= 10:
                FCLogger.debug('    Header:    [{}]\t[{}]'.format(' '.join(head for head in inputHeaders),
                                                                  ' '.join(head for head in outputHeaders) if len(self.headers) >= self.config[0] + self.config[-1] else ''))

            else:
                FCLogger.debug('    Header:    [{} {} ... {} {}]\t[{}]'.format(inputHeaders[0], inputHeaders[1], inputHeaders[-2], inputHeaders[-1],
                                                                               ' '.join(head for head in outputHeaders) if len(self.headers) >= self.config[0] + self.config[-1] else ''))

            if needFuzzy:
                for vecNum, vector in enumerate(self._rawData):
                    inputVector = vector[:self.config[0]]

                    if showExpectedVector:
                        expectedVector = vector[len(vector) - self.config[-1]:]

                    else:
                        expectedVector = None

                    FCLogger.debug('    Vector #{}:'.format(vecNum))
                    classificationResults.append(self.ClassificationResultForOneVector(inputVector, expectedVector, needFuzzy))

            else:
                for vecNum, vector in enumerate(self._rawDefuzData):
                    inputVector = vector[:self.config[0]]

                    if showExpectedVector:
                        expectedVector = vector[len(vector) - self.config[-1]:]

                    else:
                        expectedVector = None

                    FCLogger.debug('    Vector #{}:'.format(vecNum))
                    classificationResults.append(self.ClassificationResultForOneVector(inputVector, expectedVector))

        else:
            FCLogger.debug('Some classification results:')

            if len(inputHeaders) <= 10:
                FCLogger.debug('    Header:    [{}]\t[{}]'.format(' '.join(head for head in inputHeaders),
                                                                  ' '.join(head for head in outputHeaders) if len(self.headers) >= self.config[0] + self.config[-1] else ''))

            else:
                FCLogger.debug('    Header:    [{} {} ... {} {}]\t[{}]'.format(inputHeaders[0], inputHeaders[1], inputHeaders[-2], inputHeaders[-1],
                                                                               ' '.join(head for head in outputHeaders) if len(self.headers) >= self.config[0] + self.config[-1] else ''))

            if len(self._rawData) <= 10:
                for vecNum, rawLine in enumerate(self._rawData):
                    FCLogger.debug('    Vector #{}:'.format(vecNum))
                    classificationResults.append(
                        self.ClassificationResultForOneVector(rawLine[:self.config[0]] if not needFuzzy else self._rawDefuzData[vecNum][:self.config[0]],
                                                              rawLine[len(rawLine) - self.config[-1]:] if not needFuzzy else self._rawDefuzData[vecNum][len(self._rawDefuzData[vecNum]) - self.config[-1]:], needFuzzy))

            else:
                FCLogger.debug('    Vector #0:')
                classificationResults.append(
                    self.ClassificationResultForOneVector(self._rawData[0][:self.config[0]] if not needFuzzy else self._rawDefuzData[0][:self.config[0]],
                                                          self._rawData[0][len(self._rawData[0]) - self.config[-1]:] if not needFuzzy else self._rawDefuzData[0][len(self._rawDefuzData[0]) - self.config[-1]:], needFuzzy))
                FCLogger.debug('    Vector #1:')
                classificationResults.append(
                    self.ClassificationResultForOneVector(self._rawData[1][:self.config[0]] if not needFuzzy else self._rawDefuzData[1][:self.config[0]],
                                                          self._rawData[1][len(self._rawData[1]) - self.config[-1]:] if not needFuzzy else self._rawDefuzData[1][len(self._rawDefuzData[1]) - self.config[-1]:], needFuzzy))
                FCLogger.debug('    ... skipped ...')
                FCLogger.debug('    Vector #{}:'.format(len(self._rawData) - 2))
                classificationResults.append(
                    self.ClassificationResultForOneVector(self._rawData[-2][:self.config[0]] if not needFuzzy else self._rawDefuzData[-2][:self.config[0]],
                                                          self._rawData[-2][len(self._rawData[-2]) - self.config[-1]:] if not needFuzzy else self._rawDefuzData[-2][len(self._rawDefuzData[-2]) - self.config[-1]:], needFuzzy))
                FCLogger.debug('    Vector #{}:'.format(len(self._rawData) - 1))
                classificationResults.append(
                    self.ClassificationResultForOneVector(self._rawData[-1][:self.config[0]] if not needFuzzy else self._rawDefuzData[-1][:self.config[0]],
                                                          self._rawData[-1][len(self._rawData[-1]) - self.config[-1]:] if not needFuzzy else self._rawDefuzData[-1][len(self._rawDefuzData[-1]) - self.config[-1]:], needFuzzy))

        return classificationResults

    def Train(self):
        """
        Realize training mechanism.
        """
        noTrainErrors = True  # successful train flag

        try:
            if self._epochs > 0:
                if self.trainer:
                    started = datetime.now()
                    FCLogger.info('Max epochs: {}'.format(self._epochs))

                    if os.path.exists(self.bestNetworkFile):
                        os.remove(self.bestNetworkFile)  # remove old best network before training

                    if os.path.exists(self.bestNetworkInfoFile):
                        os.remove(self.bestNetworkInfoFile)  # remove best network info file before training

                    for epoch in range(self._epochs):
                        FCLogger.info('Current epoch: {}'.format(self.trainer.epoch + 1))

                        # Updating current error status:
                        if epoch == 0 or (epoch + 1) % self._epochsToUpdate == 0:
                            # Current results is the list of result vectors: [[defuzInput, outputVector, defuzExpectedVector, errorVector], ...]:
                            currentResult = self.ClassificationResults(fullEval=True, needFuzzy=True, showExpectedVector=True)

                            # Counting error as length of list with only vectors with euclidian norm between expected vector and current vector given error > self._epsilon:
                            vectorsWithErrors = [res[3] for res in currentResult if math.sqrt(sum([item * item for item in res[3]])) > self._epsilon]
                            self.currentFalsePercent = len(vectorsWithErrors) * 100 / len(currentResult)

                            errorString = '{:.1f}% ({} of {})'.format(self.currentFalsePercent,
                                                                      len(vectorsWithErrors),
                                                                      len(currentResult))
                            FCLogger.info("    - number of error vectors: {}".format(errorString))

                        # Saving current best network after first epoch only:
                        if epoch > 0 and self.currentFalsePercent < self.bestNetworkFalsePercent:
                            if os.path.exists(self.networkFile):
                                self.bestNetworkFalsePercent = self.currentFalsePercent

                                FCLogger.info('Best network found:')
                                FCLogger.info('    Config: {}'.format(self.config))
                                FCLogger.info('    Epoch: {}'.format(epoch + 1))
                                FCLogger.info("    Number of error vectors (Euclidian norm > epsilon): {}".format(errorString))

                                with open(self.bestNetworkInfoFile, 'w') as fH:
                                    fH.write('Best network common results:\n')
                                    fH.write('    Config: {}\n'.format(self.config))
                                    fH.write('    Epoch: {}\n'.format(epoch + 1))
                                    fH.write("    Number of error vectors (Euclidian norm > epsilon): {}\n".format(errorString))

                                shutil.copyfile(self.networkFile, self.bestNetworkFile)
                                FCLogger.info('Best network saved to file: {}'.format(os.path.abspath(self.bestNetworkFile)))
                                FCLogger.info('Common information about best network saved to file: {}'.format(os.path.abspath(self.bestNetworkInfoFile)))

                        # Stop train if best netwok found:
                        if self.currentFalsePercent <= self._stop:
                            FCLogger.info('Current percent of false classificated vectors is {:.1f}% less than stop value {:.1f}%.'.format(self.currentFalsePercent, self._stop))
                            break

                        # Main step of training network at current epoch:
                        self.trainer.train()  # training network
                        if (epoch + 1) % self._epochsToUpdate != 0:
                            self.ClassificationResults(fullEval=False, needFuzzy=False)  # show some results for ethalon vectors

                        if epoch % 10 == 0:
                            self.SaveNetwork()

                    if self._epochs > 1:
                        self.SaveNetwork()

                    # Replace last network with the best network:
                    if os.path.exists(self.networkFile) and os.path.exists(self.bestNetworkFile):

                        os.remove(self.networkFile)
                        shutil.copyfile(self.bestNetworkFile, self.networkFile)

                        FCLogger.info('Current network replace with the best network.')

                    FCLogger.info('Duration of learning: {}'.format(datetime.now() - started))

                else:
                    raise Exception('Trainer instance not created!')

            else:
                FCLogger.warning('Epoch of learning count is 0. Train not run!')

        except:
            noTrainErrors = False
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while Training Fuzzy Network!')

        finally:
            return noTrainErrors

    def CreateReport(self, results=None, fuzzyOutput=True):
        """
        Creating text report after classificate vector-candidates.
        results is a list of tuples in ClassificationResults() format.
        fuzzyOutput is a key for show fuzzy values if True.
        """
        FCLogger.debug('Creating Classificate Report File...')

        noReportCreationErrors = True  # successful of Creating Report process flag

        try:
            if not results:
                results = self.ClassificationResults(fullEval=True, needFuzzy=fuzzyOutput)

            with open(self.reportFile, 'w') as fH:
                fH.write('Neuronet: {}\n\n'.format(os.path.abspath(self.networkFile)))
                fH.write('{}\n\n'.format(self.scale))
                fH.write('Classification results for candidates vectors:\n\n')
                head = '    Header: [{}]\t[{}]\n'.format(' '.join(header for header in self.headers[:self.config[0]]),
                                                         ' '.join(header for header in self.headers[len(self.headers) - self.config[-1]:]) if len(self.headers) >= self.config[0] + self.config[-1] else '')
                fH.write(head)
                fH.write('    {}\n'.format('-' * len(head) if len(head) < 100 else '-' * 100))

                for result in results:
                    if fuzzyOutput:
                        fH.write('    Input: {}\tOutput: {}{}\n'.format(
                            result[0], result[1], '\tExpected: {}'.format(result[2]) if result[2] else ''))

                    else:
                        fH.write('    Input: {}\tOutput: {}{}\n'.format(
                            result[0], result[1], '\tExpected: {}\tError: {}'.format(result[2], result[3]) if result[2] else ''))

            FCLogger.info('Classificate Report File created: {}'.format(os.path.abspath(self.reportFile)))

        except:
            noReportCreationErrors = False
            FCLogger.error(traceback.format_exc())
            FCLogger.error('An error occurred while Classificate Report creating!')

        finally:
            return noReportCreationErrors


if __name__ == "__main__":
    pass