import os
from os.path import isfile, splitext, join
import shutil
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import pdb
import math

import numpy as np

#import web_view_mesh

#
# Auto3dgm
#

class Auto3dgm(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Auto3dgm" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Auto3dgm"]
    self.parent.dependencies = []
    self.parent.contributors = ["Doug Boyer (Duke University)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

    # module level data

#
# Auto3dgmModuleData
#
  """May be a temporary stand-in class, this stores module-level results and data
  not stored in MRML scene"""
class Auto3dgmData():
  def __init__(self):
    self.dataset = None
    """ To be discussed?
    1) Store all the datasets into dataset collection
    2) Add phase1 and phase2 sampled points. The idea here is that
    once we have subsampled the mesh, we dont want to access thesbased    on the slider value (that the user can change, resulting in a crash if not subsampled again). Instead: Record the keys everytime subsampling is done
    """
    self.datasetCollection = None
    self.phase1SampledPoints = None
    self.phase2SampledPoints = None
    self.aligned_meshes = []
#
# Auto3dgmWidget
#

class Auto3dgmWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    
      # Make sure mosek is installed
    try:
      import mosek
    except ModuleNotFoundError as e:
      if slicer.util.confirmOkCancelDisplay("Auto3dgm requires 'mosek' python package. Click OK to download it now. It may take a few minues. Please also download an academic mosek license from https://www.mosek.com/products/academic-licenses/ and save the license file in the lib folder. More details about installing a mosek license can be found on https://toothandclaw.github.io/installations/"):
        slicer.util.pip_install('mosek')
        import mosek
  
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    #Widget variables
    self.meshFolder = None
    self.outputFolder = None
    self.visualizationMeshFolder = None
    self.outputFolderPrepared = False
    self.Auto3dgmData = Auto3dgmData()
    self.webWidget = None
    self.serverNode = None

    # Instantiate and connect widgets ...
    tabsWidget = qt.QTabWidget()
    setupTab = qt.QWidget()
    setupTabLayout = qt.QFormLayout(setupTab)
    
    runTab = qt.QWidget()
    runTabLayout = qt.QFormLayout(runTab)
    outTab = qt.QWidget()
    outTabLayout = qt.QFormLayout(outTab)

    tabsWidget.addTab(setupTab, "Setup")
    tabsWidget.addTab(runTab, "Run")
    tabsWidget.addTab(outTab, "Visualize")
    self.layout.addWidget(tabsWidget)

    self.setupSetupTab(setupTabLayout)
    self.setupRunTab(runTabLayout)
    self.setupOutTab(outTabLayout)

  ### SETUP TAB WIDGETS AND BEHAVIORS ###

  def setupSetupTab(self, setupTabLayout):
    inputfolderWidget=ctk.ctkCollapsibleButton()
    inputfolderLayout=qt.QFormLayout(inputfolderWidget)
    inputfolderWidget.text = "Input and output folder"
    setupTabLayout.addRow(inputfolderWidget)

    self.meshInputText, volumeInLabel, self.inputFolderButton=self.textIn('Input folder','Choose input folder', '')

    self.inputFolderButton.connect('clicked(bool)', self.selectMeshFolder)
    self.loadButton=qt.QPushButton("Load Data")
    self.loadButton.enabled=False
    self.loadButton.connect('clicked(bool)', self.onLoad)
    self.LMText, volumeInLabel, self.LMbutton=self.textIn('Input Directory','..', '')
    
    self.checkMeshButton=qt.QPushButton("Check Mesh Quality")
    self.checkMeshButton.toolTip = "Check NaN values in vertices."
    self.checkMeshButton.enabled=False
    self.checkMeshButton.connect('clicked(bool)', self.checkMeshOnLoad)
    # self.singleStepGroupBoxLayout.addWidget(self.checkMeshButton)
    
    self.meshOutputText, volumeOutLabel, self.outputFolderButton=self.textIn('Output folder','Choose output folder', '')
    self.outputFolderButton.connect('clicked(bool)', self.selectOutputFolder)

    inputfolderLayout.addRow(volumeInLabel)#,1,1)
    inputfolderLayout.addRow(self.meshInputText)#,1,2)
    inputfolderLayout.addRow(self.inputFolderButton)#,1,3)
    inputfolderLayout.addRow(self.loadButton)
    inputfolderLayout.addRow(self.checkMeshButton)
    inputfolderLayout.addRow(self.meshOutputText)
    inputfolderLayout.addRow(self.outputFolderButton)
    self.LMbutton.connect('clicked(bool)', self.selectMeshFolder)

    self.parameterWidget = ctk.ctkCollapsibleButton()
    self.parameterLayout = qt.QFormLayout(self.parameterWidget)
    self.parameterWidget.text = "Parameters"
    setupTabLayout.addRow(self.parameterWidget)

    self.maxIterSliderWidget = ctk.ctkSliderWidget()
    self.maxIterSliderWidget.setDecimals(0)
    self.maxIterSliderWidget.singleStep = 1
    self.maxIterSliderWidget.minimum = 1
    self.maxIterSliderWidget.maximum = 5000
    self.maxIterSliderWidget.value = 1000
    self.maxIterSliderWidget.setToolTip("Maximum possible number of iterations for pairwise alignment optimization.")
    self.parameterLayout.addRow("Maximum iterations", self.maxIterSliderWidget)

    self.reflectionCheckBox = qt.QCheckBox()
    self.reflectionCheckBox.checked = 0
    self.reflectionCheckBox.setToolTip("Whether meshes can be reflected/mirrored to achieve more optimal alignments.")
    self.parameterLayout.addRow("Allow reflection", self.reflectionCheckBox)

    self.fpsSeed = qt.QSpinBox()
    self.fpsSeed.setSpecialValueText('-')
    self.parameterLayout.addRow("Optional FPS Seed", self.fpsSeed)

    self.phaseChoiceComboBox = qt.QComboBox()
    self.phaseChoiceComboBox.addItem("1 (Single Alignment Pass)")
    self.phaseChoiceComboBox.addItem("2 (Double Alignment Pass)")
    self.phaseChoiceComboBox.setCurrentIndex(1)
    self.parameterLayout.addRow("Analysis phases", self.phaseChoiceComboBox)

    self.phase1PointNumber = qt.QSpinBox()
    self.phase1PointNumber.setMinimum(1)
    self.phase1PointNumber.setMaximum(100000)
    self.phase1PointNumber.setValue(10)
    self.parameterLayout.addRow("Phase 1 Points", self.phase1PointNumber)

    self.phase2PointNumber = qt.QSpinBox()
    self.phase2PointNumber.setMinimum(1)
    self.phase2PointNumber.setMaximum(1000000)
    self.phase2PointNumber.setValue(40)
    self.parameterLayout.addRow("Phase 2 Points", self.phase2PointNumber)

  def selectMeshFolder(self):
      self.meshFolder=qt.QFileDialog().getExistingDirectory()
      self.meshInputText.setText(self.meshFolder)
      try:
        self.loadButton.enabled = bool(self.meshFolder)
      except AttributeError:
        self.loadButton.enable = False

  def selectOutputFolder(self):
    self.outputFolder=qt.QFileDialog().getExistingDirectory()
    self.meshOutputText.setText(self.outputFolder)

  def onLoad(self):
    self.Auto3dgmData.datasetCollection=Auto3dgmLogic.createDataset(self.meshFolder)
    print(self.Auto3dgmData.datasetCollection)
    try:
      self.subStepButton.enabled = bool(self.meshFolder)
      self.phase1StepButton.enabled = bool(self.meshFolder)
      self.phase2StepButton.enabled = bool(self.meshFolder)
      self.allStepsButton.enabled = bool(self.meshFolder)
      self.checkMeshButton.enabled = bool(self.meshFolder)
    except AttributeError:
      self.subStepButton.enable = False
      self.phase1StepButton.enabled = False
      self.phase2StepButton.enabled = False
      self.allStepsButton.enabled = False
      self.checkMeshButton.enabled = False

  def checkMeshOnLoad(self):
    Auto3dgmLogic.checkMeshQuality(meshes=self.Auto3dgmData.datasetCollection.datasets[0])

  def prepareOutputFolder(self):
    if (not os.path.exists(self.outputFolder+"/lowres/")):
      os.mkdir(self.outputFolder+"/lowres/")
    if (not os.path.exists(self.outputFolder+"/highres/")):
      os.mkdir(self.outputFolder+"/highres/")
    if (not os.path.exists(self.outputFolder+"/aligned/")):
      os.mkdir(self.outputFolder+"/aligned/")
    self.outputFolderPrepared=True

  ### RUN TAB WIDGETS AND BEHAVIORS ###

  def setupRunTab(self, runTabLayout):
    self.singleStepGroupBox = qt.QGroupBox("Run individual steps")
    self.singleStepGroupBoxLayout = qt.QVBoxLayout()
    self.singleStepGroupBoxLayout.setSpacing(5)
    self.singleStepGroupBox.setLayout(self.singleStepGroupBoxLayout)
    runTabLayout.addRow(self.singleStepGroupBox)

    self.subStepButton = qt.QPushButton("Subsample")
    self.subStepButton.toolTip = "Run subsample step of analysis, creating collections of subsampled points per mesh."
    self.subStepButton.connect('clicked(bool)', self.subStepButtonOnLoad)
    self.subStepButton.enabled=False
    self.singleStepGroupBoxLayout.addWidget(self.subStepButton)

    self.phase1StepButton = qt.QPushButton("Phase 1")
    self.phase1StepButton.toolTip = "Run the first analysis phase, aligning meshes based on low resolution subsampled points."
    self.phase1StepButton.connect('clicked(bool)', self.phase1StepButtonOnLoad)
    self.phase1StepButton.enabled=False
    self.singleStepGroupBoxLayout.addWidget(self.phase1StepButton)

    self.phase2StepButton = qt.QPushButton("Phase 2")
    self.phase2StepButton.toolTip = "Run the second analysis phase, aligning meshes based on high resolution subsampled points."
    self.phase2StepButton.connect('clicked(bool)', self.phase2StepButtonOnLoad)
    self.phase2StepButton.enabled=False
    self.singleStepGroupBoxLayout.addWidget(self.phase2StepButton)

    self.allStepsButton = qt.QPushButton("Run all steps")
    self.allStepsButton.toolTip = "Run all possible analysis steps and phases."
    self.allStepsButton.connect('clicked(bool)', self.allStepsButtonOnLoad)
    self.allStepsButton.enabled=False
    runTabLayout.addRow(self.allStepsButton)

    runTabLayout.setVerticalSpacing(15)

  def subStepButtonOnLoad(self):
    print("Mocking a call to the Logic service AL002.1")
    # Store the keys
    self.Auto3dgmData.phase1SampledPoints = self.phase1PointNumber.value
    self.Auto3dgmData.phase2SampledPoints = self.phase2PointNumber.value
    self.Auto3dgmData.fpsSeed=self.fpsSeed.value
    Auto3dgmLogic.subsample(self.Auto3dgmData,list_of_pts = [self.phase1PointNumber.value,self.phase2PointNumber.value], meshes=self.Auto3dgmData.datasetCollection.datasets[0])
    print("Dataset collection updated")
    print(self.Auto3dgmData.datasetCollection.datasets)

  def phase1StepButtonOnLoad(self):
    self.Auto3dgmData.datasetCollection.add_analysis_set(Auto3dgmLogic.correspondence(self.Auto3dgmData, self.reflectionCheckBox.checked, phase=1),"Phase 1")
    self.Auto3dgmData.phase1SampledPoints = self.phase1PointNumber.value
    print('Exporting data')
    Auto3dgmLogic.exportData(self.Auto3dgmData, self.outputFolder, phases = [1])

  def phase2StepButtonOnLoad(self):
    self.Auto3dgmData.datasetCollection.add_analysis_set(Auto3dgmLogic.correspondence(self.Auto3dgmData, self.reflectionCheckBox.checked, phase=2),"Phase 2")
    self.Auto3dgmData.phase1SampledPoints = self.phase1PointNumber.value
    Auto3dgmLogic.exportData(self.Auto3dgmData, self.outputFolder, phases = [2])

  def allStepsButtonOnLoad(self):
    self.Auto3dgmData.phase1SampledPoints = self.phase1PointNumber.value
    self.Auto3dgmData.phase2SampledPoints = self.phase2PointNumber.value
    Auto3dgmLogic.runAll(self.Auto3dgmData, self.reflectionCheckBox.checked)
    Auto3dgmLogic.exportData(self.Auto3dgmData, self.outputFolder, phases = [1, 2])

  ### OUTPUT TAB WIDGETS AND BEHAVIORS

  def setupOutTab(self, outTabLayout):
    # visualizationinputfolderWidget=ctk.ctkCollapsibleButton()
    # visualizationinputfolderLayout=qt.QFormLayout(visualizationinputfolderWidget)
    # visualizationinputfolderWidget.text = ""
    # outTabLayout.addRow(visualizationinputfolderWidget)

    # self.visualizationmeshInputText, visualizationvolumeInLabel, self.visualizationinputFolderButton=self.textIn('Input folder','Choose input folder', '')

    # visualizationinputfolderLayout.addRow(visualizationvolumeInLabel)#,1,1)
    # visualizationinputfolderLayout.addRow(self.visualizationmeshInputText)#,1,2)
    # visualizationinputfolderLayout.addRow(self.visualizationinputFolderButton)#,1,3)

    # self.visualizationinputFolderButton.connect('clicked(bool)', self.visualizationSelectMeshFolder)

    self.visMeshGroupBox = qt.QGroupBox("Visualize aligned meshes")
    self.visMeshGroupBoxLayout = qt.QVBoxLayout()
    self.visMeshGroupBoxLayout.setSpacing(5)
    self.visMeshGroupBox.setLayout(self.visMeshGroupBoxLayout)
    outTabLayout.addRow(self.visMeshGroupBox)

    # self.visStartServerButton = qt.QPushButton("Start mesh visualization server")
    # self.visStartServerButton.toolTip = "Start server for visualizing aligned meshes. Be sure to stop server before quitting Slicer."
    # self.visStartServerButton.connect('clicked(bool)', self.visStartServerButtonOnLoad)
    # self.visMeshGroupBoxLayout.addWidget(self.visStartServerButton)

    self.visPhase1Button = qt.QPushButton("View Phase 1 alignment")
    self.visPhase1Button.toolTip = "Visualize aligned meshes with alignment based on low resolution subsampled points."
    self.visPhase1Button.connect('clicked(bool)', self.visPhase1ButtonOnLoad)
    self.visPhase1Button.enabled = True
    self.visMeshGroupBoxLayout.addWidget(self.visPhase1Button)

    self.visPhase2Button = qt.QPushButton("View Phase 2 alignment")
    self.visPhase2Button.toolTip = "Visualize aligned meshes with alignment based on high resolution subsampled points."
    self.visPhase2Button.connect('clicked(bool)', self.visPhase2ButtonOnLoad)
    self.visPhase2Button.enabled = True
    self.visMeshGroupBoxLayout.addWidget(self.visPhase2Button)

    visFrame = ctk.ctkCollapsibleButton()
    visFrame.text="Landmark Options"
    visFrameLayout= qt.QGridLayout(visFrame)
    outTabLayout.addWidget(visFrame)
    
    self.scaleLMKSlider = ctk.ctkSliderWidget()
    self.scaleLMKSlider.singleStep = .1
    self.scaleLMKSlider.minimum = 0
    self.scaleLMKSlider.maximum = 10
    self.scaleLMKSlider.value = 3
    self.scaleLMKSlider.setToolTip("Set scale for landmark glyphs")
    scaleLMKSliderLabel=qt.QLabel("Glyph scale")
    visFrameLayout.addWidget(scaleLMKSliderLabel,4,1)
    visFrameLayout.addWidget(self.scaleLMKSlider,4,2)
    self.scaleLMKSlider.connect('valueChanged(double)', self.scaleLMKGlyph)

    self.scaleLMKSliderText = ctk.ctkSliderWidget()
    self.scaleLMKSliderText.singleStep = .1
    self.scaleLMKSliderText.minimum = 0
    self.scaleLMKSliderText.maximum = 10
    self.scaleLMKSliderText.value = 0
    self.scaleLMKSliderText.setToolTip("Set scale for landmark label")
    scaleLMKSliderLabelText=qt.QLabel("Label scale")
    visFrameLayout.addWidget(scaleLMKSliderLabelText,5,1)
    visFrameLayout.addWidget(self.scaleLMKSliderText,5,2)
    self.scaleLMKSliderText.connect('valueChanged(double)', self.scaleLMKText)
    
    outTabLayout.setVerticalSpacing(15)
  
  def scaleLMKGlyph(self):
      LMKNodeNum = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLMarkupsFiducialDisplayNode")
      for i in range(LMKNodeNum):
        LMKNode = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLMarkupsFiducialDisplayNode")
        LMKNode.SetGlyphScale(self.scaleLMKSlider.value)

  def scaleLMKText(self):
      LMKNodeNum = slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLMarkupsFiducialDisplayNode")
      for i in range(LMKNodeNum):
        LMKNode = slicer.mrmlScene.GetNthNodeByClass(i, "vtkMRMLMarkupsFiducialDisplayNode")
        LMKNode.SetTextScale(self.scaleLMKSliderText.value)

  def visSubButtonOnLoad(self):
    print("Mocking a call to the Logic service AL003.3, maybe others")

  #  def visStartServerButtonOnLoad(self):
  #    viewerTmp = os.path.join(self.outputFolder, 'viewer_tmp')
  #    if self.visStartServerButton.text == "Start mesh visualization server":
  #      self.visPhase1Button.enabled = True
  #      self.visPhase2Button.enabled = True
  #      self.visStartServerButton.setText("Stop Mesh Visualization Server")
  #      Auto3dgmLogic.prepareDirs(viewerTmp)
  #      self.serverNode = Auto3dgmLogic.serveWebViewer(viewerTmp)
  #    else:
  #      self.visPhase1Button.enabled = False
  #      self.visPhase2Button.enabled = False
  #      self.visStartServerButton.setText("Start mesh visualization server")
  #      if self.serverNode:
  #        self.serverNode.Cancel()
  #      Auto3dgmLogic.removeDir(viewerTmp)

  def visPhase1ButtonOnLoad(self):
    #viewerTmp = os.path.join(self.outputFolder, 'viewer_tmp')
    #Auto3dgmLogic.copyAlignedMeshes(viewerTmp, self.outputFolder, phase = 1)
    #self.webWidget = Auto3dgmLogic.createWebWidget()
    viewMeshFolder = os.path.join(self.outputFolder, 'phase1/aligned_meshes')
    viewLmkFolder = os.path.join(self.outputFolder, 'phase1/aligned_landmarks')
    Auto3dgmLogic.viewAlignedMeshWithinSlicer(viewMeshFolder, viewLmkFolder)
  

  def visPhase2ButtonOnLoad(self):
    #viewerTmp = os.path.join(self.outputFolder, 'viewer_tmp')
    #Auto3dgmLogic.copyAlignedMeshes(viewerTmp, self.outputFolder, phase = 1)
    #self.webWidget = Auto3dgmLogic.createWebWidget()
    viewMeshFolder = os.path.join(self.outputFolder, 'phase2/aligned_meshes')
    viewLmkFolder = os.path.join(self.outputFolder, 'phase2/aligned_landmarks')
    Auto3dgmLogic.viewAlignedMeshWithinSlicer(viewMeshFolder, viewLmkFolder)
  
  # def outPhase1ButtonOnLoad(self):
  #   print("Mocking a call to the Logic service AL003.1")
  #   if self.outputFolderPrepared==False:
  #     self.prepareOutputFolder()
  #   meshes = self.Auto3dgmData.datasetCollection.datasets[self.Auto3dgmData.phase1SampledPoints][self.Auto3dgmData.phase1SampledPoints]
  #   rotations = self.Auto3dgmData.datasetCollection.analysis_sets["Phase 1"].globalized_alignment['r']
  #   permutations = self.Auto3dgmData.datasetCollection.analysis_sets["Phase 1"].globalized_alignment['p']
  #   meshes = Auto3dgmLogic.landmarksFromPseudoLandmarks(meshes,permutations,rotations)
  #   for mesh in meshes:
  #       cfilename = self.outputFolder+"/lowres/"+mesh.name
  #       Auto3dgmLogic.saveNumpyArrayToCsv(mesh.vertices,cfilename)

  # def outPhase2ButtonOnLoad(self):
  #   print("Mocking a call to the Logic service AL003.1")
  #   if self.outputFolderPrepared==False:
  #     self.prepareOutputFolder()
  #   meshes = self.Auto3dgmData.datasetCollection.datasets[self.Auto3dgmData.phase2SampledPoints][self.Auto3dgmData.phase2SampledPoints]
  #   rotations = self.Auto3dgmData.datasetCollection.analysis_sets["Phase 2"].globalized_alignment['r']
  #   permutations = self.Auto3dgmData.datasetCollection.analysis_sets["Phase 2"].globalized_alignment['p']
  #   meshes = Auto3dgmLogic.landmarksFromPseudoLandmarks(meshes,permutations,rotations)
  #   for mesh in meshes:
  #       cfilename = self.outputFolder+"/highres/"+mesh.name
  #       Auto3dgmLogic.saveNumpyArrayToCsv(mesh.vertices,cfilename)

  # def outVisButtonOnLoad(self):
  #   print("Mocking a call to the Logic service unnamed visualization output service")

  def textIn(self,label, dispText, toolTip):
    """ a function to set up the appearnce of a QlineEdit widget.
    the widget is returned.
    """
    # set up text line
    textInLine=qt.QLineEdit();
    textInLine.setText(dispText)
    textInLine.toolTip = toolTip
    # set up label
    lineLabel=qt.QLabel()
    lineLabel.setText(label)

    # make clickable button
    button=qt.QPushButton(dispText)
    return textInLine, lineLabel, button

  # def visualizationSelectMeshFolder(self):
  #   self.visualizationMeshFolder=qt.QFileDialog().getExistingDirectory()
  #   self.visualizationmeshInputText.setText(self.visualizationMeshFolder)
  #   slicer.app.coreIOManager().loadFile(self.visualizationMeshFolder+"/MSTmatrix.csv")
  #   slicer.app.coreIOManager().loadFile(self.visualizationMeshFolder+"/distancematrix.csv")
  #   print(self.visualizationMeshFolder)

  def cleanup(self):
    pass

  def onImportAligned(self):
    Auto3dgmLogic.alignOriginalMeshes(self.Auto3dgmData)
    # Auto3dgmLogic.saveAlignedMeshesForViewer(self.Auto3dgmData)
    Auto3dgmLogic.saveAlignedMeshes(self.Auto3dgmData, os.path.join(self.outputFolder, 'aligned'))
    print("Meshes exported")

#
# Auto3dgmLogic
#

class Auto3dgmLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def runAll(Auto3dgmData, mirror):
    Auto3dgmLogic.subsample(Auto3dgmData,[Auto3dgmData.phase1SampledPoints,Auto3dgmData.phase2SampledPoints],Auto3dgmData.datasetCollection.datasets[0])
    print("Subsampling complete.")
    Auto3dgmData.datasetCollection.add_analysis_set(Auto3dgmLogic.correspondence(Auto3dgmData, mirror, phase=1),"Phase 1")
    print("Phase 1 complete.")
    Auto3dgmData.datasetCollection.add_analysis_set(Auto3dgmLogic.correspondence(Auto3dgmData, mirror, phase=2),"Phase 2")
    print("Phase 2 complete.")

  # Logic service function AL001.001 Create dataset
  def createDataset(inputdirectory):
    from auto3dgm_nazar.dataset.datasetfactory import DatasetFactory
    dataset = DatasetFactory.ds_from_dir(inputdirectory,center_scale=True)
    return dataset

  # Logic service function AL002.1 Subsample

  # In: List of points, possibly just one
  # list of meshes
  def subsample(Auto3dgmData,list_of_pts, meshes):
    from auto3dgm_nazar.mesh.subsample import Subsample
    ss = Subsample(pointNumber=list_of_pts, meshes=meshes, seed={},center_scale=True)
    for point in list_of_pts:
      names = []
      meshes = []
      for key in ss.ret[point]['output']['output']:
        mesh = ss.ret[point]['output']['output'][key]
        meshes.append(mesh)
      dataset = {}
      dataset[point] = meshes
      Auto3dgmData.datasetCollection.add_dataset(dataset,point)
    return(Auto3dgmData)
 
  def createDatasetCollection(dataset, name):
    import auto3dgm_nazar
    datasetCollection=auto3dgm_nazar.dataset.datasetcollection.DatasetCollection(datasets = [dataset],dataset_names = [name])
    return datasetCollection
  
  def checkMeshQuality(meshes):
    badMesh = []
    for mesh in meshes:
      if np.isnan(np.sum(mesh.vertices)):
        print(mesh.name)
        badMesh.append(mesh.name)
    if len(badMesh) > 0:
      slicer.util.confirmOkCancelDisplay("Mesh quality check failed. Please clean the meshes listed in the python console.")
    else:
      slicer.util.confirmOkCancelDisplay("Mesh quality check passed. ")

  def correspondence(Auto3dgmData, mirror, phase = 1):
    from auto3dgm_nazar.analysis.correspondence import Correspondence
    if phase == 1:
      npoints = Auto3dgmData.phase1SampledPoints
    else:
      npoints = Auto3dgmData.phase2SampledPoints
    meshes = Auto3dgmData.datasetCollection.datasets[npoints][npoints]
    corr = Correspondence(meshes=meshes, mirror=mirror)
    print("Correspondence compute for Phase " + str(phase))
    return(corr)
  
  def landmarksFromPseudoLandmarks(subsampledMeshes,permutations,rotations):
    import auto3dgm_nazar
    from auto3dgm_nazar.mesh.meshfactory import MeshFactory
    meshes = []
    for i in range(len(subsampledMeshes)):
      mesh = subsampledMeshes[i]
      perm = permutations[i]
      rot = rotations[i]
      V = mesh.vertices
      scaledV = mesh.initial_vertices
      lmtranspose = scaledV.T @ perm
      #landmarks = scaledV
      landmarks = np.transpose(np.matmul(rot,lmtranspose))
      mesh = auto3dgm_nazar.mesh.meshfactory.MeshFactory.mesh_from_data(vertices=landmarks,name=mesh.name, center_scale=False, deep=True)
      meshes.append(mesh)
    return(meshes)

  def landmarksOSSFromPseudoLandmarks(subsampledMeshes,permutations):
    import auto3dgm_nazar
    from auto3dgm_nazar.mesh.meshfactory import MeshFactory
    meshes = []
    for i in range(len(subsampledMeshes)):
      mesh = subsampledMeshes[i]
      perm = permutations[i]
      V = mesh.vertices
      scaledV = mesh.initial_vertices
      lmtranspose = scaledV.T @ perm
      #landmarks = scaledV
      landmarks = np.transpose(lmtranspose)
      mesh = auto3dgm_nazar.mesh.meshfactory.MeshFactory.mesh_from_data(vertices=landmarks,name=mesh.name, center_scale=False, deep=True)
      meshes.append(mesh)
    return(meshes)

  def saveTFM(m, filename):
    # convert 4 x 4 transform matrix to tfm file
    # compute the inverse of m
    invm = np.linalg.inv(m)
    # create a tfm file format
    filename = filename + ".tfm"
    file = open(filename,"w")
    file.write("#Insight Transform File V1.0\n")
    file.write("#Transform 0\n")
    file.write("Transform: AffineTransform_double_3_3\n")
    file.write("Parameters: ")
    # print the 3 x 3 submatrix in the upper left corner
    for i in range(0,3):
        # print each column
        file.write(str(m[0,i]) + " " + str(m[1,i]) + " " + str(m[2,i]) + " ")
    # print the last column with the first two entries sign flipped
    file.write(str(-1 * m[0,3]) + " " + str(-1 * m[1,3]) + " " + str(m[1,3]) + "\n")
    # print a last line
    file.write("FixedParameters: 0 0 0")
    file.close()

  def saveNumpyArrayToCsv(array,filename):
    np.savetxt(filename+".csv",array,delimiter = ",",fmt = "%s")
  
  def saveNumpyArrayToFcsv(array,filename):
      l = np.shape(array)[0]
      fname2 = filename + ".fcsv"
      file = open(fname2,"w")
      file.write("# Markups fiducial file version = 4.4 \n")
      file.write("# columns = id,x,y,z,vis,sel \n")
      for i in range(l):
          file.write("p" + str(i) + ",")
          file.write(str(array[i,0]) + "," + str(array[i,1]) + "," + str(array[i,2]) + ",1,1 \n")
      file.close()

  def alignOriginalMeshes(Auto3dgmData, phase = 2):
    import auto3dgm_nazar
    from auto3dgm_nazar.mesh.meshfactory import MeshFactory
    if phase == 1:
      corr = Auto3dgmData.datasetCollection.analysis_sets['Phase 1']
    elif phase == 2:
      corr = Auto3dgmData.datasetCollection.analysis_sets['Phase 2']
    else:
      raise ValueError('Unaccepted phase number passed to Auto3dgmLogic.exportAlignedLandmarks')

    meshes = Auto3dgmData.datasetCollection.datasets[0]
    Auto3dgmData.aligned_meshes = []
    for t in range(len(meshes)):
      R = corr.globalized_alignment['r'][t]
      verts=meshes[t].vertices
      faces=meshes[t].faces
      name=meshes[t].name
      #vertices = verts
      vertices=np.transpose(np.matmul(R,np.transpose(verts)))
      faces=faces.astype('int64')
      aligned_mesh=auto3dgm_nazar.mesh.meshfactory.MeshFactory.mesh_from_data(vertices, faces=faces, name=name, center_scale=False, deep=True)
      Auto3dgmData.aligned_meshes.append(aligned_mesh)
    return(Auto3dgmData)

  def saveAlignedMeshes(Auto3dgmData,outputFolder):
    from auto3dgm_nazar.mesh.meshexport import MeshExport
    if not os.path.exists(outputFolder):
      os.makedirs(outputFolder)
    for mesh in Auto3dgmData.aligned_meshes:
      print(os.path.join(outputFolder, mesh.name))
      MeshExport.writeToFile(outputFolder, mesh, format='ply')
    print("Aligned meshes saved. \n" )

  def exportData(Auto3dgmData, outputFolder, phases=[1, 2]):
    acceptable_phases = [1, 2]
    for p in phases:
      if p not in acceptable_phases:
        raise ValueError('Unacceptable phase number passed to Auto3dgmLogic.exportData')
      
      exportFolder = os.path.join(outputFolder, 'phase' + str(p))
      subDirs = ['aligned_meshes', 'aligned_landmarks', 'rotation', 'scale_info', 'landmarks_OSS', 'original_meshes']

      Auto3dgmLogic.prepareDirs(exportFolder, subDirs)
      Auto3dgmLogic.alignOriginalMeshes(Auto3dgmData, p)
      Auto3dgmLogic.saveAlignedMeshes(Auto3dgmData, os.path.join(exportFolder, subDirs[0]))
      Auto3dgmLogic.exportAlignedLandmarks(Auto3dgmData, os.path.join(exportFolder, subDirs[1]), p)
      Auto3dgmLogic.exportRotations(Auto3dgmData, os.path.join(exportFolder, subDirs[2]), p)
      Auto3dgmLogic.exportScaleInfo(Auto3dgmData, os.path.join(exportFolder, subDirs[3]))
      Auto3dgmLogic.exportLandmarksOSS(Auto3dgmData, os.path.join(exportFolder, subDirs[4]), p)
      Auto3dgmLogic.exportOriginalMeshes(Auto3dgmData, os.path.join(exportFolder, subDirs[5]))
    print("All computation done. \n" )

  def exportAlignedLandmarks(Auto3dgmData, exportFolder, phase = 2):
    from auto3dgm_nazar.mesh.meshexport import MeshExport
    from auto3dgm_nazar.mesh.meshfactory import MeshFactory
    if phase == 1:
      n = Auto3dgmData.phase1SampledPoints
      label = "Phase 1"
    elif phase == 2:
      n = Auto3dgmData.phase2SampledPoints
      label = "Phase 2"
    else:
      raise ValueError('Unaccepted phase number passed to Auto3dgmLogic.exportAlignedLandmarks')

    m = Auto3dgmData.datasetCollection.datasets[n][n]
    r = Auto3dgmData.datasetCollection.analysis_sets[label].globalized_alignment['r']
    p = Auto3dgmData.datasetCollection.analysis_sets[label].globalized_alignment['p']
    landmarks = Auto3dgmLogic.landmarksFromPseudoLandmarks(m, p, r)

    for l in landmarks:
      #Auto3dgmLogic.saveNumpyArrayToFcsv(l.vertices, os.path.join(exportFolder, l.name))
      Auto3dgmLogic.saveLandmarks(l.vertices, os.path.join(exportFolder, l.name))

  def exportLandmarksOSS(Auto3dgmData, exportFolder, phase = 2):
    from auto3dgm_nazar.mesh.meshexport import MeshExport
    from auto3dgm_nazar.mesh.meshfactory import MeshFactory
    if phase == 1:
      n = Auto3dgmData.phase1SampledPoints
      label = "Phase 1"
    elif phase == 2:
      n = Auto3dgmData.phase2SampledPoints
      label = "Phase 2"
    else:
      raise ValueError('Unaccepted phase number passed to Auto3dgmLogic.exportAlignedLandmarks')
    
    m = Auto3dgmData.datasetCollection.datasets[n][n]
    p = Auto3dgmData.datasetCollection.analysis_sets[label].globalized_alignment['p']
    landmarks = Auto3dgmLogic.landmarksOSSFromPseudoLandmarks(m, p)

    mmesh = Auto3dgmData.datasetCollection.datasets[0]
    scaleDict = {}
    centerDict = {}
    for idx, mesh in enumerate(mmesh):
      m = mesh.initial_scale
      c = mesh.initial_centroid
      # m = np.vstack((m.T, [-1*c[0], -1*c[1], c[2]]))
      scaleDict[mesh.name] = m
      centerDict[mesh.name] = c

    for l in landmarks:
      m = scaleDict[l.name]
      c = centerDict[l.name]
      lmkOSS = m * l.vertices + c
      Auto3dgmLogic.saveLandmarks(lmkOSS, os.path.join(exportFolder, l.name))

  def exportRotations(Auto3dgmData, exportFolder, phase = 2):
    if phase == 1:
      label = "Phase 1"
      n = Auto3dgmData.phase1SampledPoints
    elif phase == 2:
      label = "Phase 2"
      n = Auto3dgmData.phase2SampledPoints
    else:
      raise ValueError('Unaccepted phase number passed to Auto3dgmLogic.')
    
    m = Auto3dgmData.datasetCollection.datasets[n][n]
    r = Auto3dgmData.datasetCollection.analysis_sets[label].globalized_alignment['r']

    for idx in range(len(m)):
      mesh = m[idx]
      rot = r[idx]
      # rot = np.linalg.inv(rot)
      # pad rot into 4 x 4 transform matrix in slicer
      rot[2][0] = -1 * rot[2][0]
      rot[2][1] = -1 * rot[2][1]
      rot[0][2] = -1 * rot[0][2]
      rot[1][2] = -1 * rot[1][2]
      rot = np.vstack((rot.T, [0, 0, 0]))  # add a 4-th column for center info
      rot = np.vstack((rot.T, [0, 0, 0, 1])) # add a 4-row
      Auto3dgmLogic.saveNumpyArrayToCsv(rot, os.path.join(exportFolder, mesh.name))
      Auto3dgmLogic.saveTransform(rot, os.path.join(exportFolder, mesh.name))

  def exportScaleInfo(Auto3dgmData, exportFolder):
    mmesh = Auto3dgmData.datasetCollection.datasets[0]
    for idx, mesh in enumerate(mmesh):
        filename = os.path.join(exportFolder, mesh.name)
        m = (1/mesh.initial_scale) * np.diag([1, 1, 1])
        c = (1/mesh.initial_scale) * mesh.initial_centroid
        m = np.vstack((m.T, [1*c[0], 1*c[1], -c[2]]))
        m = np.vstack((m.T, [0, 0, 0, 1]))
        Auto3dgmLogic.saveNumpyArrayToCsv(m, filename)
        Auto3dgmLogic.saveTransform(m, filename)

  def saveLandmarks(m, filename):
    fiducialNode = slicer.vtkMRMLMarkupsFiducialNode() # Create a markups node for imported points
    l = np.shape(m)[0]
    for landmark in range(l):
        coordinates = [float(-1*m[landmark,0]), float(-1*m[landmark,1]), float(m[landmark,2])]
        fiducialNode.AddFiducialFromArray(coordinates, str(landmark)) #insert fiducial named by landmark number
    slicer.mrmlScene.AddNode(fiducialNode)
    fiducialNode.SetName('LM') # set name to subject name, removing new line char
    path = filename + '.fcsv'
    slicer.util.saveNode(fiducialNode, path)
    slicer.mrmlScene.RemoveNode(fiducialNode)  #remove node from scene
    #fiducialNode.RemoveAllControlPoints() # remove all landmarks from node (new markups version)
    fiducialNode.RemoveAllMarkups()  # remove all landmarks from node

  def saveTransform(m, filename):
    matrix_vtk = vtk.vtkMatrix4x4()
    for i in range(4):
      for j in range(4):
        matrix_vtk.SetElement(i,j,m[i][j])
    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix_vtk)
    transformNode =  slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode', 'LT')
    transformNode.SetAndObserveTransformToParent(transform)
    filename = filename + '.h5'
    slicer.util.saveNode(transformNode,filename)
    slicer.mrmlScene.RemoveNode(transformNode)

  def exportOriginalMeshes(Auto3dgmData, outputFolder):
    import auto3dgm_nazar
    from auto3dgm_nazar.mesh.meshexport import MeshExport
    if not os.path.exists(outputFolder):
      os.makedirs(outputFolder)
    for mesh in Auto3dgmData.datasetCollection.datasets[0]:
      mesh_orig = auto3dgm_nazar.mesh.meshfactory.MeshFactory.mesh_from_data(vertices=mesh.initial_vertices,faces=mesh.faces, name=mesh.name, center_scale=False, deep=True)
      MeshExport.writeToFile(outputFolder, mesh_orig, format='ply')

  def exportScaleInfoOld(Auto3dgmData, exportFolder):
    n = Auto3dgmData.phase1SampledPoints
    m = Auto3dgmData.phase2SampledPoints

    mmesh = Auto3dgmData.datasetCollection.datasets[0]
    mlmk1 = Auto3dgmData.datasetCollection.datasets[n][n]
    mlmk2 = Auto3dgmData.datasetCollection.datasets[m][m]

    for idx, mesh in enumerate(mmesh):
      lmk1 = mlmk1[idx]
      lmk2 = mlmk2[idx]
      filename = os.path.join(exportFolder, mesh.name) + ".csv"
      file = open(filename,"w")
      # use below to obtain raw center and scale info
      file.write("# center and scale information. \n")
      file.write("# original center and scale. \n")
      file.write("# first landmarks center and scale. \n")
      file.write("# second landmarks center and scale. \n")
      file.write(str(mesh.initial_centroid[0]) + "," + str(mesh.initial_centroid[1]) + "," + str(mesh.initial_centroid[2]) + "," + str(mesh.initial_scale) + " \n")
      file.write(str(lmk1.initial_centroid[0]) + "," + str(lmk1.initial_centroid[1]) + "," + str(lmk1.initial_centroid[2]) + "," + str(lmk1.initial_scale) + " \n")
      file.write(str(lmk2.initial_centroid[0]) + "," + str(lmk2.initial_centroid[1]) + "," + str(lmk2.initial_centroid[2]) + "," + str(lmk2.initial_scale) + " \n")
      file.close()
  
  def prepareDirs(exportFolder, subDirs=[]):
    if not os.path.exists(exportFolder):
      os.makedirs(exportFolder)
    for subdir in subDirs:
      d = os.path.join(exportFolder, subdir)
      if not os.path.exists(d):
        os.makedirs(d)

  def removeDir(trashFolder):
    if os.path.exists(trashFolder):
      shutil.rmtree(trashFolder)

  def copyAlignedMeshes(targetFolder, outputFolder, phase = 2):
    if phase not in [1, 2]:
      raise ValueError('Unaccepted phase number passed to Auto3dgmLogic.copyAlignedMeshes')

    for item in os.listdir(targetFolder):
      s = os.path.join(targetFolder, item)
      if os.path.isfile(s):
        os.unlink(s)

    srcFolder = os.path.join(outputFolder, 'phase' + str(phase), 'aligned_meshes')
    for item in os.listdir(srcFolder):
      s = os.path.join(srcFolder, item)
      d = os.path.join(targetFolder, item)
      if os.path.isfile(s):
        shutil.copy2(s, d)

  def serveWebViewer(viewFolder):
    parameters = { 'MeshDirectory': viewFolder }
    return slicer.cli.run(slicer.modules.meshviewer, None, parameters)
  
  def createWebWidget():
    webWidget = slicer.qSlicerWebWidget()
    slicerGeometry = slicer.util.mainWindow().geometry
    webWidget.size = qt.QSize(slicerGeometry.width(),slicerGeometry.height())
    webWidget.pos = qt.QPoint(slicerGeometry.x() + 256, slicerGeometry.y() + 128)
    webWidget.url = "http://localhost:8000"
    webWidget.show()
    return webWidget

  def viewAlignedMeshWithinSlicer(viewMeshFolder, viewLmkFolder):
      slicer.mrmlScene.Clear(0)
      modelDir = viewMeshFolder
      modelFileExt = "ply"
      numberOfColumns = 4
      modelFiles = list(f for f in os.listdir(modelDir) if f.endswith('.' + modelFileExt))
      
      markupDir = viewLmkFolder
      markupFileExt = "fcsv"
      
      # Create a custom layout
      numberOfRows = min(int(math.ceil(len(modelFiles)/numberOfColumns)), 4)
      customLayoutId= 3311  # we pick a random id that is not used by others
      slicer.app.setRenderPaused(True)
      customLayout = '<layout type="vertical">'
      viewIndex = 0
      for rowIndex in range(numberOfRows):
        customLayout += '<item><layout type="horizontal">'
        for colIndex in range(numberOfColumns):
          name = os.path.basename(modelFiles[viewIndex]) if viewIndex < len(modelFiles) else "compare "+str(viewIndex)
          customLayout += '<item><view class="vtkMRMLViewNode" singletontag="'+name
          customLayout += '"><property name="viewlabel" action="default">'+name+'</property></view></item>'
          viewIndex += 1
        customLayout += '</layout></item>'

      customLayout += '</layout>'
      if not slicer.app.layoutManager().layoutLogic().GetLayoutNode().SetLayoutDescription(customLayoutId, customLayout):
          slicer.app.layoutManager().layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)

      slicer.app.layoutManager().setLayout(customLayoutId)
      
      # Add a transform node
      c = 2000
      transformNode = slicer.vtkMRMLTransformNode()
      slicer.mrmlScene.AddNode(transformNode)
      transformMatrixNP = np.array(
      [[c, 0, 0, 0],
       [0, c, 0, 0],
       [0, 0, c, 0],
       [0, 0, 0, 1]])
      transformNode.SetAndObserveMatrixTransformToParent(slicer.util.vtkMatrixFromArray(transformMatrixNP))
      
      # Load and show each model in a view
      for modelIndex, modelFile in enumerate(modelFiles):
        if modelIndex < numberOfColumns * numberOfRows:
          # set a viewNode
          name = os.path.basename(modelFile)
          viewNode = slicer.mrmlScene.GetSingletonNode(name, "vtkMRMLViewNode")
          viewNode.LinkedControlOn()
          # set a modelNode
          modelNode = slicer.util.loadModel(modelDir+"/"+modelFile)
          modelNode.SetAndObserveTransformNodeID(transformNode.GetID())
          modelNode.GetDisplayNode().AddViewNodeID(viewNode.GetID())
          # Show only one set of landmark in each view
          markupFile = os.path.splitext(modelFile)[0] + '.' + markupFileExt
          markupNode =  slicer.util.loadMarkupsFiducialList(markupDir+"/"+markupFile)[1]
          markupNode.SetAndObserveTransformNodeID(transformNode.GetID())
          mDisplayNode = markupNode.GetDisplayNode()
          mDisplayNode.SetTextScale(0)
          mDisplayNode.SetGlyphScale(4)
          mDisplayNode.AddViewNodeID(viewNode.GetID())

      slicer.app.setRenderPaused(False)


class Auto3dgmTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Auto3dgm1()

  def test_Auto3dgm1(self):
    pass



