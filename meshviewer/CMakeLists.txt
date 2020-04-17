#-----------------------------------------------------------------------------
set(MODULE_NAME meshviewer)

#-----------------------------------------------------------------------------
# If the module only consists of ${MODULE_NAME}.py and ${MODULE_NAME}.xml
# then no changes are needed in the lines below.

set(CLI_DEST "${CMAKE_BINARY_DIR}/${Slicer_CLIMODULES_BIN_DIR}")
set(CLI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}")

add_custom_command(
  OUTPUT "${CLI_DEST}/${MODULE_NAME}.py" "${CLI_DEST}/${MODULE_NAME}.xml"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${CLI_DEST}"
  COMMAND "${CMAKE_COMMAND}" -E copy "${CLI_SOURCE}/${MODULE_NAME}.py" "${CLI_DEST}"
  COMMAND "${CMAKE_COMMAND}" -E copy "${CLI_SOURCE}/${MODULE_NAME}.xml" "${CLI_DEST}"
  COMMAND "${CMAKE_COMMAND}" -E copy_directory "${CLI_SOURCE}/web_view_mesh/" "${CLI_DEST}/web_view_mesh/"
  DEPENDS "${CLI_SOURCE}/${MODULE_NAME}.xml" "${CLI_SOURCE}/${MODULE_NAME}.py"
  )

add_custom_target(${MODULE_NAME} ALL
  SOURCES "${CLI_SOURCE}/${MODULE_NAME}.py" "${CLI_SOURCE}/${MODULE_NAME}.xml"
  DEPENDS "${CLI_DEST}/${MODULE_NAME}.py" "${CLI_DEST}/${MODULE_NAME}.xml"
  COMMENT "Copying ${MODULE_NAME} files to  ${CLI_DEST}"
  )

install(PROGRAMS ${MODULE_NAME}.py ${MODULE_NAME}.xml
  DESTINATION "${Slicer_INSTALL_CLIMODULES_BIN_DIR}"
  COMPONENT Runtime
  )
install(DIRECTORY "${CLI_SOURCE}/web_view_mesh"
  DESTINATION "${Slicer_INSTALL_CLIMODULES_BIN_DIR}"
  COMPONENT Runtime
  USE_SOURCE_PERMISSIONS
  )
