cmake_minimum_required(VERSION 3.20)

project(AetherflowHost LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(
  AETHERFLOW_BUILD_GRPC_SERVICE
  "Build the native CaptureControl gRPC service"
  OFF
)

add_library(aetherflow_supervisor STATIC host/supervisor.cpp)
target_include_directories(aetherflow_supervisor PUBLIC include)

add_library(aetherflow_capture_control STATIC host/capture_control.cpp)
target_include_directories(aetherflow_capture_control PUBLIC include)
target_link_libraries(aetherflow_capture_control PUBLIC aetherflow_supervisor)

add_executable(native_harness host/native_harness.cpp)
target_include_directories(native_harness PRIVATE include)

if(AETHERFLOW_BUILD_GRPC_SERVICE)
  find_package(Protobuf REQUIRED)

  if(TARGET protobuf::libprotobuf)
    set(AETHERFLOW_PROTOBUF_TARGET protobuf::libprotobuf)
  else()
    set(AETHERFLOW_PROTOBUF_TARGET ${Protobuf_LIBRARIES})
  endif()

  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(GRPCPP QUIET IMPORTED_TARGET grpc++)
  endif()

  if(TARGET PkgConfig::GRPCPP)
    set(AETHERFLOW_GRPCPP_TARGET PkgConfig::GRPCPP)
  else()
    find_package(gRPC CONFIG REQUIRED)
    set(AETHERFLOW_GRPCPP_TARGET gRPC::grpc++)
  endif()

  if(Protobuf_PROTOC_EXECUTABLE)
    set(PROTOC_EXECUTABLE "${Protobuf_PROTOC_EXECUTABLE}")
  else()
    find_program(PROTOC_EXECUTABLE protoc REQUIRED)
  endif()
  find_program(GRPC_CPP_PLUGIN_EXECUTABLE grpc_cpp_plugin REQUIRED)

  set(CAPTURE_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/proto/capture.proto")
  set(CAPTURE_PROTO_SRC "${CMAKE_CURRENT_BINARY_DIR}/capture.pb.cc")
  set(CAPTURE_PROTO_HDR "${CMAKE_CURRENT_BINARY_DIR}/capture.pb.h")
  set(CAPTURE_GRPC_SRC "${CMAKE_CURRENT_BINARY_DIR}/capture.grpc.pb.cc")
  set(CAPTURE_GRPC_HDR "${CMAKE_CURRENT_BINARY_DIR}/capture.grpc.pb.h")

  add_custom_command(
    OUTPUT
      "${CAPTURE_PROTO_SRC}"
      "${CAPTURE_PROTO_HDR}"
      "${CAPTURE_GRPC_SRC}"
      "${CAPTURE_GRPC_HDR}"
    COMMAND
      "${PROTOC_EXECUTABLE}"
    ARGS
      --cpp_out "${CMAKE_CURRENT_BINARY_DIR}"
      --grpc_out "${CMAKE_CURRENT_BINARY_DIR}"
      -I "${CMAKE_CURRENT_SOURCE_DIR}/proto"
      --plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN_EXECUTABLE}
      "${CAPTURE_PROTO}"
    DEPENDS "${CAPTURE_PROTO}"
    VERBATIM
  )

  add_library(
    aetherflow_capture_proto STATIC
    "${CAPTURE_PROTO_SRC}"
    "${CAPTURE_PROTO_HDR}"
    "${CAPTURE_GRPC_SRC}"
    "${CAPTURE_GRPC_HDR}"
  )
  target_include_directories(
    aetherflow_capture_proto
    PUBLIC "${CMAKE_CURRENT_BINARY_DIR}"
  )
  target_link_libraries(
    aetherflow_capture_proto
    PUBLIC
      ${AETHERFLOW_PROTOBUF_TARGET}
      ${AETHERFLOW_GRPCPP_TARGET}
  )

  add_library(
    aetherflow_capture_control_service STATIC
    host/capture_control_service.cpp
  )
  target_include_directories(
    aetherflow_capture_control_service
    PUBLIC include
  )
  target_link_libraries(
    aetherflow_capture_control_service
    PUBLIC
      aetherflow_capture_control
      aetherflow_capture_proto
  )

  add_executable(
    aetherflow_capture_control_server
    host/capture_control_server.cpp
  )
  target_link_libraries(
    aetherflow_capture_control_server
    PRIVATE
      aetherflow_capture_control_service
  )
endif()
