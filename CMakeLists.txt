cmake_minimum_required(VERSION 3.13.4)

project(Auto3dgm)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://toothandclaw.github.io")
set(EXTENSION_CATEGORY "Auto3dgm")
set(EXTENSION_CONTRIBUTORS "Doug Boyer (Duke University)")
set(EXTENSION_DESCRIPTION "Auto3dgm allows for comparative analysis of 3D digital models representing biological surfaces. Unlike other three-dimensional geometric morphometric (3DGM) methods this software uses a fully automated procedure for placing landmarks on the surfaces. This allows for the alignment of surfaces followed by measuring distance between surfaces with minimal user intervention.
The goal of this NSF funded project is to extend Auto3dgm to open source software platform and make it more user-friendly to a larger scientific community. Towards this goal, we developed the Auto3dgm module in 3D Slicer, an open source software platform for medical image informatics, image processing, and three-dimensional visualization. The module enables scientists to perform Auto3dgm on a collection of shapes effectively within 3D Slicer. The package also alllows users to visualize and save the aligned results to local machines for downstream analysis.
This project is supported by a NSF Advances in Biological Informatics Collaborative grant to Murat Maga (ABI-1759883), Adam Summers (ABI-1759637) and Doug Boyer (ABI-1759839).")
set(EXTENSION_ICONURL "http://www2.stat.duke.edu/~hmk16/auto3dgm/auto3dgmlogo.png")
set(EXTENSION_SCREENSHOTURLS "http://www2.stat.duke.edu/~hmk16/auto3dgm/auto3dgmscreenshot.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Auto3dgm)
add_subdirectory(meshviewer)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
