vcpkg_from_git(
  OUT_SOURCE_PATH SOURCE_PATH
  URL https://github.com/giobuilds/io.git
  REF bbd0eafabfadaed8e1a32dcda35d7a9d38400ba8
  HEAD_REF linux-port
)

vcpkg_check_features(OUT_FEATURE_OPTIONS FEATURE_OPTIONS
    FEATURES
      documentation BUILD_DOCUMENTATION
)

vcpkg_cmake_configure(
  SOURCE_PATH ${SOURCE_PATH}
  OPTIONS
  ${FEATURE_OPTIONS}
  -DBUILD_TESTING=OFF
  -DVCPKG_USE_HOST_TOOLS=ON
  -DVCPKG_HOST_TRIPLET=${HOST_TRIPLET}
  -DCMAKE_BUILD_TYPE=${CARBON_BUILD_TYPE}
)

vcpkg_cmake_install()

vcpkg_cmake_config_fixup()
set(BUILD_PATHS
  "${CURRENT_PACKAGES_DIR}/bin/*.dll"
  "${CURRENT_PACKAGES_DIR}/debug/bin/*.dll"
  "${CURRENT_PACKAGES_DIR}/bin/*.pyd"
  "${CURRENT_PACKAGES_DIR}/debug/bin/*.pyd"
)
vcpkg_copy_pdbs(
  BUILD_PATHS ${BUILD_PATHS}
)
ccp_externalize_apple_debuginfo()
