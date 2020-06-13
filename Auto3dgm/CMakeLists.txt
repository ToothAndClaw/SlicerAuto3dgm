#-----------------------------------------------------------------------------
set(MODULE_NAME Auto3dgm)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

install(DIRECTORY "auto3dgm_nazar"
  DESTINATION "${Slicer_INSTALL_QTSCRIPTEDMODULES_BIN_DIR}"
  COMPONENT Runtime
  USE_SOURCE_PERMISSIONS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
