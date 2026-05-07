import Foundation
import Combine

// MARK: - Character type

enum CharacterType: String, CaseIterable {
    case rabbit      = "rabbit"
    case brownRabbit = "brownRabbit"

    var displayName: String {
        switch self {
        case .rabbit:      return "부니 (흰토끼)"
        case .brownRabbit: return "두니 (갈색토끼)"
        }
    }
}

// MARK: - Store

class CharacterStore: ObservableObject {
    static let shared = CharacterStore()

    @Published var selected: CharacterType = .rabbit {
        didSet { UserDefaults.standard.set(selected.rawValue, forKey: "character.selected") }
    }

    init() {
        if let raw  = UserDefaults.standard.string(forKey: "character.selected"),
           let type = CharacterType(rawValue: raw) {
            selected = type
        } else {
            selected = .rabbit
        }
    }
}
