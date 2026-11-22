import Foundation

enum Interface {
    // build.sh installs the tables in Search.app. SwiftPM keeps them in its resource bundle.
    private static let bundle: Bundle = Bundle.main.url(forResource: "Interface", withExtension: "strings",
        subdirectory: nil, localization: "en") == nil ? .module : .main

    static func text(_ key: String) -> String {
        bundle.localizedString(forKey: key, value: key, table: "Interface")
    }
}
