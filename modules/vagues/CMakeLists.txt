# Module custom : vagues de bots niveau 1
set(LIBRARY_NAME vagues)

file(GLOB vagues_source ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/*.h)
source_group("vagues" FILES ${vagues_source})
set(LIBRARY_SRCS ${vagues_source})

if (BUILD_PLAYERBOTS)
  include_directories(${CMAKE_SOURCE_DIR}/src/modules/PlayerBots)
  include_directories(${CMAKE_SOURCE_DIR}/src/modules/PlayerBots/playerbot)
  include_directories(${CMAKE_SOURCE_DIR}/dep/g3dlite)
  add_definitions(-DENABLE_PLAYERBOTS)
  add_definitions(-DCMANGOS)
endif()

include_directories(${CMAKE_SOURCE_DIR}/src/modules/modules/src)
add_definitions(-DENABLE_MODULES)
add_definitions(-DENABLE_VAGUES)

if ( ${CMAKE_PROJECT_NAME} MATCHES "Classic")
  add_definitions(-DEXPANSION=0)
  add_definitions(-DMANGOSBOT_ZERO)
endif()

add_library(${LIBRARY_NAME} STATIC ${LIBRARY_SRCS})

target_link_libraries(${LIBRARY_NAME}
  modules
  shared
  RecastNavigation::Detour
)

if(UNIX)
  if (NOT (CMAKE_SYSTEM_NAME STREQUAL "FreeBSD" OR CMAKE_SYSTEM_NAME STREQUAL "NetBSD"))
    target_link_libraries(${LIBRARY_NAME} dl)
  endif()
endif()

set_target_properties(${LIBRARY_NAME} PROPERTIES PROJECT_LABEL "Vagues")
set_target_properties(${LIBRARY_NAME} PROPERTIES FOLDER "Modules")
