import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            AtlasWebAppView()
                .tabItem { Label("Full Atlas", systemImage: "globe") }

            NavigationStack {
                UniverseView()
            }
            .tabItem { Label("Native Preview", systemImage: "sparkles") }

            NavigationStack {
                SystemExplorerView()
            }
            .tabItem { Label("System Preview", systemImage: "map") }

            NavigationStack {
                StoryVisualizerView()
            }
            .tabItem { Label("Story Preview", systemImage: "play.rectangle") }

            NavigationStack {
                MiniLabView()
            }
            .tabItem { Label("Lab Preview", systemImage: "slider.horizontal.3") }

            NavigationStack {
                CompassView()
            }
            .tabItem { Label("Compass Preview", systemImage: "safari") }
        }
        .tint(.cyan)
    }
}

struct AtlasBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .scrollContentBackground(.hidden)
            .background(
                LinearGradient(
                    colors: [
                        Color(red: 0.02, green: 0.05, blue: 0.10),
                        Color(red: 0.04, green: 0.12, blue: 0.18),
                        Color(red: 0.00, green: 0.08, blue: 0.13)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
            )
    }
}

extension View {
    func atlasBackground() -> some View {
        modifier(AtlasBackground())
    }
}

struct HeroHeader: View {
    let title: String
    let subtitle: String
    let symbol: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image("PreviewImages")
                .resizable()
                .scaledToFill()
                .frame(height: 150)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(alignment: .bottomLeading) {
                    LinearGradient(colors: [.clear, .black.opacity(0.75)], startPoint: .top, endPoint: .bottom)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    VStack(alignment: .leading, spacing: 6) {
                        Label(title, systemImage: symbol)
                            .font(.title2.bold())
                        Text(subtitle)
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.78))
                    }
                    .padding(14)
                    .foregroundStyle(.white)
                }
        }
    }
}

struct MetricPill: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title.uppercased())
                .font(.caption2.weight(.bold))
                .foregroundStyle(.cyan.opacity(0.82))
            Text(value)
                .font(.headline)
                .foregroundStyle(.white)
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(.white.opacity(0.12)))
    }
}
