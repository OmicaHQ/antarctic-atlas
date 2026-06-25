# Install Antarctic Atlas on an iPhone

This project can be built on GitHub's hosted macOS runner, then installed from Windows with a sideloading tool. You do not need to own a Mac for this route.

## Route A: Windows + GitHub Actions + Sideloadly

Use this first. It is the most direct route from the current repository to your iPhone.

1. Push the repository to GitHub, including the `ios/` folder and `.github/workflows/` files.
2. Open the repository on GitHub.
3. Go to **Actions**.
4. Select **iOS Unsigned IPA**.
5. Click **Run workflow**.
6. Wait for the workflow to finish.
7. Open the finished workflow run.
8. Download the artifact named **AntarcticAtlas-unsigned-ipa**.
9. Unzip the artifact. You should get `AntarcticAtlas-unsigned.ipa`.
10. On Windows, install Sideloadly from `https://sideloadly.io/`.
11. Connect your iPhone to the PC with USB and trust the computer on the iPhone.
12. Open Sideloadly.
13. Drag `AntarcticAtlas-unsigned.ipa` into Sideloadly.
14. Select your connected iPhone.
15. Enter your Apple ID in Sideloadly.
16. Click **Start**.
17. On the iPhone, open **Settings > General > VPN & Device Management**.
18. Trust the developer profile for your Apple ID.
19. Open **AntarcticAtlas** from the Home Screen.

Notes:

- With a free Apple ID, sideloaded apps normally expire after several days and must be reinstalled.
- Sideloadly may ask for an app-specific password if your Apple ID uses two-factor authentication.
- This is not App Store distribution. It is a developer-style sideload for personal testing.

## Route B: Signed IPA from GitHub Actions

Use this if you have an Apple Developer Program account and want a signed installable build.

Add these GitHub repository secrets:

- `IOS_BUILD_CERTIFICATE_BASE64`: Base64-encoded `.p12` signing certificate.
- `IOS_P12_PASSWORD`: Password for that `.p12`.
- `IOS_PROVISION_PROFILE_BASE64`: Base64-encoded `.mobileprovision` profile for `com.omica.antarcticatlas`.
- `IOS_DEVELOPMENT_TEAM`: Your Apple Developer Team ID.
- `IOS_KEYCHAIN_PASSWORD`: Any strong temporary password for the CI keychain.

Then run the **iOS Signed IPA** workflow from GitHub Actions and download the **AntarcticAtlas-signed-ipa** artifact.

## Route C: TestFlight later

For wider testing, the best long-term path is TestFlight. That requires an Apple Developer Program account, an App Store Connect app record, and an uploaded App Store signed build.
