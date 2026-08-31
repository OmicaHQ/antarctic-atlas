import AppKit
import Observation
import SwiftUI

@MainActor
@Observable
final class Theme {
    let accent = Color(red: 0.18, green: 0.56, blue: 0.98)
    let iceBlue = Color(red: 0.38, green: 0.72, blue: 1.00)
    let deepOcean = Color(red: 0.018, green: 0.075, blue: 0.13)
    let polarNight = Color(red: 0.012, green: 0.035, blue: 0.073)
    let sidebarSelection = Color(red: 0.08, green: 0.24, blue: 0.40)

    // These are intentionally branded surfaces instead of generic system gray.
    // Materials and native controls still inherit the user's macOS appearance.
    var windowBackground: Color { Color(red: 0.012, green: 0.035, blue: 0.073) }
    var controlBackground: Color { Color(red: 0.035, green: 0.10, blue: 0.17) }
    var raisedBackground: Color { Color(red: 0.045, green: 0.13, blue: 0.22) }
    var separator: Color { Color.white.opacity(0.10) }
    var secondaryLabel: Color { Color.white.opacity(0.62) }

    var detailBackground: LinearGradient {
        LinearGradient(
            colors: [
                Color(red: 0.018, green: 0.09, blue: 0.16),
                polarNight,
                Color(red: 0.015, green: 0.045, blue: 0.09),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    var sidebarBackground: LinearGradient {
        LinearGradient(
            colors: [
                Color(red: 0.026, green: 0.095, blue: 0.16),
                Color(red: 0.015, green: 0.055, blue: 0.10),
            ],
            startPoint: .top,
            endPoint: .bottom
        )
    }

    func tint(for module: AppModule) -> Color {
        switch module {
        case .researchUniverse: iceBlue
        case .antarcticSystem: Color(red: 0.20, green: 0.67, blue: 0.76)
        case .aiVisualizer: Color(red: 0.56, green: 0.47, blue: 0.90)
        case .miniResearchLab: Color(red: 0.20, green: 0.68, blue: 0.50)
        case .researchCompass: Color(red: 0.91, green: 0.57, blue: 0.22)
        case .rawPaper: Color(red: 0.45, green: 0.58, blue: 0.72)
        }
    }

    func selectionAnimation(reduceMotion: Bool) -> Animation? {
        reduceMotion ? nil : .smooth(duration: 0.22)
    }
}

enum AtlasMetrics {
    static let sidebarIdealWidth: CGFloat = 276
    static let inspectorIdealWidth: CGFloat = 322
    static let contentMaxWidth: CGFloat = 1_180
    static let cardCornerRadius: CGFloat = 14
    static let sidebarRowCornerRadius: CGFloat = 10
    static let compactSpacing: CGFloat = 8
    static let standardSpacing: CGFloat = 16
    static let generousSpacing: CGFloat = 24
}

struct AtlasCardStyle: ViewModifier {
    @Environment(\.colorScheme) private var colorScheme

    func body(content: Content) -> some View {
        content
            .padding(AtlasMetrics.standardSpacing)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: AtlasMetrics.cardCornerRadius, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: AtlasMetrics.cardCornerRadius, style: .continuous)
                    .strokeBorder(.white.opacity(colorScheme == .dark ? 0.11 : 0.30), lineWidth: 0.75)
            }
    }
}

extension View {
    func atlasCard() -> some View {
        modifier(AtlasCardStyle())
    }
}
