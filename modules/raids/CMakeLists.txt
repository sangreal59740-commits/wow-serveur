# Module custom : raids a 10 ou 20 joueurs
set(LIBRARY_NAME raids)

file(GLOB raids_source ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/*.h)
source_group("raids" FILES ${raids_source})
set(LIBRARY_SRCS ${raids_source})

if (BUILD_PLAYERBOTS)
  include_directories(${CMAKE_SOURCE_DIR}/src/modules/PlayerBots)
  add_definitions(-DENABLE_PLAYERBOTS)
endif()

include_directories(${CMAKE_SOURCE_DIR}/src/modules/modules/src)
add_definitions(-DENABLE_MODULES)
add_definitions(-DENABLE_RAIDS)

if ( ${CMAKE_PROJECT_NAME} MATCHES "Classic")
  add_definitions(-DEXPANSION=0)
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

set_target_properties(${LIBRARY_NAME} PROPERTIES PROJECT_LABEL "Raids")
set_target_properties(${LIBRARY_NAME} PROPERTIES FOLDER "Modules")
