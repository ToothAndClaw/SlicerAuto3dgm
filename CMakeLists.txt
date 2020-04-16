cmake_minimum_required(VERSION 3.13.4)

project(Auto3dgm)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://toothandclaw.github.io")
set(EXTENSION_CATEGORY "Auto3dgm")
set(EXTENSION_CONTRIBUTORS "Doug Boyer (Duke University)")
set(EXTENSION_DESCRIPTION "The auto3dgm Slicer Extension")
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
