// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "AntarcticAtlasNative",
    platforms: [
        .macOS(.v15)
    ],
    products: [
        .executable(name: "AntarcticAtlas", targets: ["AntarcticAtlas"])
    ],
    targets: [
        .executableTarget(
            name: "AntarcticAtlas",
            path: "Sources/AntarcticAtlas",
            resources: [
                .process("Resources")
            ]
        ),
        .testTarget(
            name: "AntarcticAtlasTests",
            dependencies: ["AntarcticAtlas"],
            path: "Tests/AntarcticAtlasTests"
        )
    ],
    swiftLanguageModes: [.v5]
)
