# -*- coding: utf-8 -*-
"""
Created on Sun Mar 31 20:27:11 2019
Update 3.31: This code can register the files in the patient floder to the files
in the atlas respectively.  And then select the best results (with higest dice socre).
Update 4.1: 
@author: lxs
"""
import SimpleITK
import os
import re
import sys
 
class TextArea(object):  
  
    def __init__(self):  
        self.buffer = []  
  
    def write(self, *args, **kwargs):  
        self.buffer.append(args)  
        
def getMetricScore(elastixLogPath):
    finalMetricValue = 0
    pattern = re.compile('Final metric value  = (?P<value>[+-.0-9]{9})')

    with open(elastixLogPath) as log:
        m = re.search(pattern, log.read())
        try:
            finalMetricValue = float(m.group('value'))
        except:
            raise Exception('Final metric value not found in "elastix.log".')
    print('The final score is %f' %finalMetricValue)
    return finalMetricValue
    
def readData(path_patient = r'.\Patient', path_atlas = r'.\Atlas'):
    """
    Read in all the data in the folder
    Returns the path of each file.
    """
    #  List of path
    atlas_path = []
    atlas_manual_path = []
    patient_path = []
    patient_manual_path = []
    #  List of images
    atlas = []
    atlas_maunal = []
    patient = []
    patienr_manual = []
    #  Read in all the atlas
    for file in os.listdir(path_atlas):
        file_name = path_atlas + '\\' + file    
        atlas_path.append(file_name + '\\' + 'mr_bffe.mhd')
        atlas_manual_path.append(file_name + '\\' + 'prostaat.mhd')
        atlas.append(SimpleITK.ReadImage(file_name + '\\' + 'mr_bffe.mhd'))
        atlas_maunal.append(SimpleITK.ReadImage(file_name + '\\' + 'prostaat.mhd'))
    #  Read in all the patients
    for file in os.listdir(path_patient):
        file_name = path_patient + '\\' + file
        patient_path.append(file_name + '\\' + 'mr_bffe.mhd')
        patient_manual_path.append(file_name + '\\' + 'prostaat.mhd')
        patient.append(SimpleITK.ReadImage(file_name + '\\' + 'mr_bffe.mhd'))
        patienr_manual.append(SimpleITK.ReadImage(file_name + '\\' + 'prostaat.mhd'))
    print('There are %d atlases data and %d patient' %(len(atlas_path), len(patient_path)))
    
    return [atlas, atlas_maunal], [patient, patienr_manual]

def register(atlas, patient, ifPrint = 0):
    """
    Do the registeration.
    First it searches all the data from the altas floder. Then all the altas are 
    registered with the files in the patient floder.
    It also records the scores in a scoreList.
    The best registratons are saved.
    atlas0 = image, atlas1 = maunal
    patient0 = image, patienr1 = manual
    """
    #  Set the parameterMap
    parameterVec = setParameters0()
    #  Initilize a SimpleElastix instance
    SimpleElastix = SimpleITK.SimpleElastix()
    if ifPrint == 1:
        SimpleElastix.LogToConsoleOn()
    #  Set the parameterMap
    SimpleElastix.SetParameterMap(parameterVec)
    SimpleElastix.SetParameter('Interpolator', 'BSplineInterpolator') 
    #  ifPrint
    if ifPrint == 0:
        SimpleElastix.PrintParameterMap()
    # A list to store results of patient image
    resultPatientImage = []
    # A list to store results of patient Manuals
    resultPatientManual = []
    # A list to store results of patient score
    reslutPatientScore = []
    #  Lood through the patient folder
    for patientImage, patientManual in zip(patient[0], patient[1]):
        #  A list to store all the reslut image
        resultImage = []
        #  A list to store all the reversed manuals
        resultManuals = []
        #  A list to store all the dice scores
        resultScore = []
        #  Set the fixed image
        SimpleElastix.SetFixedImage(patientImage)
        #  Get the origin of the fixed image
        imageOrigin = patientImage.GetOrigin()
        manualOrigin = patientManual.GetOrigin()
        #  Loop through the patient folder
        for atlasImage, atlasManual in zip(atlas[0], atlas[1]):
            #  Set the origin of moving image
            atlasImage.SetOrigin(imageOrigin)
            #  Set the moving image
            SimpleElastix.SetMovingImage(atlasImage)
            #  Do the registration
            SimpleElastix.Execute()
            print('\nOne registration done!')
            resultImage.append(SimpleElastix.GetResultImage())
            #  Get the transform Matrix
            transforMartix = SimpleElastix.GetTransformParameterMap()
            #  Apply the transform Matrix to the atlasManual
            reversedManual = SimpleITK.Transformix(atlasManual, transforMartix)
            #  Label voting
            reversedManual = SimpleITK.LabelVoting(reversedManual,1) 
            print('Label voting done!')
            #  Set the origin of reversed maunal
            reversedManual.SetOrigin(manualOrigin)
            resultManuals.append(reversedManual) 
            #  Calculate the dice score
            measureFilter = SimpleITK.LabelOverlapMeasuresImageFilter()
            #  Have to change the tolerance to make the code work
            measureFilter.SetGlobalDefaultCoordinateTolerance(1e3)
            reversedOrigin = reversedManual.GetOrigin()
            atlasManual.SetOrigin(reversedOrigin)
            measureFilter.Execute(reversedManual, atlasManual)
            print('Dice scores done!')
            diceScore = measureFilter.GetDiceCoefficient()
            resultScore.append(diceScore)
            print('The dice score is %f' %diceScore)
        resultPatientImage.append(resultImage)
        resultPatientManual.append(resultManuals)
        #reslutPatientScore.append(resultScore)
    return resultPatientImage, resultPatientManual, reslutPatientScore
    
def setParameters0():
    """
    This is the basic parameters set.
    Not to much defult values are changed
    """
    parameterVec = SimpleITK.VectorOfParameterMap()

    #rigid = SimpleITK.GetDefaultParameterMap('rigid')
    traslation = SimpleITK.GetDefaultParameterMap('translation')
    affine = SimpleITK.GetDefaultParameterMap('affine')
    bspline = SimpleITK.GetDefaultParameterMap('bspline')

    traslation['FinalBSplineInterpolationOrder'] = '0'
    affine['FinalBSplineInterpolationOrder'] = '0'
    bspline['FinalBSplineInterpolationOrder'] = '0'

    traslation['Registration'] = ['MultiMetricMultiResolutionRegistration']
    affine['Registration'] = ['MultiMetricMultiResolutionRegistration']
    bspline['Registration'] = ['MultiMetricMultiResolutionRegistration']

    traslation['Metric'] = ['AdvancedMattesMutualInformation','AdvancedNormalizedCorrelation']
    affine['Metric'] = ['AdvancedMattesMutualInformation','AdvancedNormalizedCorrelation']
    bspline['Metric'] = ['AdvancedMattesMutualInformation','AdvancedNormalizedCorrelation']
    
    traslation['Metric0Weight'] = '1'
    traslation['Metric1Weight'] = '1'
    
    affine['Metric0Weight'] = '1'
    affine['Metric1Weight'] = '1'
    
    bspline['Metric0Weight'] = '1'
    bspline['Metric1Weight'] = '1'
    #parameterVec.append(rigid)
    parameterVec.append(traslation)
    parameterVec.append(affine)
    parameterVec.append(bspline)
    return parameterVec

#%%
def mutilRegistration(resultScore, atlas, patient, ifPrint=0):
    """
    Select a the top three best results and register them to the unseen patient
    Then mix the segementation by label voting
    """
    #  Set the parameterMap
    parameterVec = setParameters0()
    #  Initilize a SimpleElastix instance
    SimpleElastix = SimpleITK.SimpleElastix()
    SimpleElastix.SetLogToFile(True)
    if ifPrint == 1:
        SimpleElastix.LogToConsoleOn()
    #  Set the parameterMap
    SimpleElastix.SetParameterMap(parameterVec)
    SimpleElastix.SetParameter('Interpolator', 'BSplineInterpolator') 
    #  ifPrint
    if ifPrint == 1:
        SimpleElastix.PrintParameterMap()
    #  A list to sotre resluts
    resultSegmentation = []

    for i in range(len(resultScore)):
        #Loop through patient data
        resultLabels = SimpleITK.VectorOfImage()
        #  Set the fixed image
        SimpleElastix.SetFixedImage(patient[0][i])
        imageOrigin = patient[0][i].GetOrigin()
        resultdownUp = sorted(resultScore[i],reverse = True)
        for j in range(3):
            topScore = resultdownUp[j]
            indexScore = resultScore[i].index(topScore)
            atlas[0][indexScore].SetOrigin(imageOrigin)
            SimpleElastix.SetMovingImage(atlas[0][indexScore])
            SimpleElastix.Execute()
            resultLabels.push_back(SimpleITK.Transformix(atlas[1][indexScore], SimpleElastix.GetTransformParameterMap()))
            print('One registration done!')
        #  Label voting to pick the mixed label
        print('One mix done!')
        fixedLabel = SimpleITK.LabelVoting(resultLabels)
        #  Calculate dice score
        measureFilter = SimpleITK.LabelOverlapMeasuresImageFilter()
        #  Have to change the tolerance to make the code work
        measureFilter.SetGlobalDefaultCoordinateTolerance(1e3)
        reversedOrigin = patient[1][i].GetOrigin()
        fixedLabel.SetOrigin(reversedOrigin)
        measureFilter.Execute(fixedLabel, patient[1][i])
        diceScore = measureFilter.GetDiceCoefficient()
        print('The dice score with mixed segmentation is %f' %diceScore)
        SimpleITK.WriteImage(fixedLabel,r'.\result\mixedSegmentation' + 'Patient%f.mhd' %diceScore)
        resultSegmentation.append(fixedLabel)

def selectResults(resultImage, resultManuals, resultScore):
    """
    Select the best results and save
    """
    resultIm = []
    resultMn = []
    resultSc = []
    for i in range(len(resultScore)):
        result = resultScore[i]
        maxPos = result.index(max(result))
        resultIm.append(resultImage[i][maxPos])
        resultMn.append(resultManuals[i][maxPos])
        resultSc.append(resultScore[i][maxPos])
    for i in range(len(resultScore)):
        result = resultScore[i]
        SimpleITK.WriteImage(resultIm[i],r'.\result\resultImage' + '(%f).mhd' %max(result))
        SimpleITK.WriteImage(resultMn[i],r'.\result\resultManual'+'(%f).mhd' %max(result))
    return resultSc, resultIm, resultMn

#%%  Do the registertion and get the list of score
atlas, patient = readData()
resultImage, resultManuals, resultScore = register(atlas, patient, ifPrint=0)
#%%  Select the best result with single atlas
resultSc, resultIm, resultMn = selectResults(resultImage, resultManuals, resultScore)
#%%  Use the top 3th best results and create a mixed segementation
#mixedLabel = mutilRegistration(resultScore, atlas, patient, ifPrint=0)