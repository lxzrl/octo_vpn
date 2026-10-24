language-name = English

choose-language = 🌐 Выберите язык / Choose your language

main-menu =
    🐙 Hi, { $name }!

    This is Octo VPN: fast VPN with no traffic or device limits.
    Choose an action:

btn-subscription = 🔑 My subscription
btn-buy = 💳 Buy subscription
btn-referrals = 👥 Invite a friend
btn-support = 💬 Support
btn-profile = 👤 Profile
btn-back = ⬅️ Back
btn-change-language = 🌐 Change language

profile =
    👤 <b>Profile</b>

    ID: <code>{ $id }</code>
    Member since: { $registered }
    Language: { $language }

coming-soon = This section is coming soon

btn-trial = 🎁 Try for free
btn-connect = 📲 How to connect
btn-subscription-page = 🌐 Subscription page
btn-extend = 💳 Extend subscription
btn-open-channel = 📢 Open the channel
btn-check-subscription = ✅ I've subscribed
btn-download-app = ⬇️ Download Happ

days = { $days ->
    [one] { $days } day
   *[other] { $days } days
}

no-subscription-trial =
    🔑 <b>My subscription</b>

    You don't have a subscription yet.
    Try it for free: { days } with no limits, all locations.

no-subscription =
    🔑 <b>My subscription</b>

    You don't have a subscription yet.

subscription-active =
    ✅ <b>Subscription active</b> until { $date } ({ days } left)

    Your connection link:
    <code>{ $url }</code>

    Add it to the app once: all locations will appear there, and you can switch at any time.

subscription-trial =
    🎁 <b>Free trial</b> until { $date } ({ days } left)

    Your connection link:
    <code>{ $url }</code>

    Add it to the app once: all locations will appear there, and you can switch at any time.

subscription-expired =
    ⛔ <b>Subscription ended</b> on { $date }

    Extend it to get access back. The link in your app stays the same.

trial-activated = 🎉 Free trial activated!
trial-already-used = You have already used the free trial
trial-need-channel =
    📢 To get { days } for free, subscribe to our channel.

    Then tap "I've subscribed".
error-try-later = Something went wrong. Please try again in a couple of minutes.

connect-choose-platform = 📲 Choose the device you will use the VPN on:

platform-ios = 🍏 iPhone / iPad
platform-android = 🤖 Android
platform-windows = 🪟 Windows
platform-macos = 💻 macOS

connect-steps =
    2. Copy the link from "My subscription" (tap it).
    3. Open Happ and tap "+" → "Paste from clipboard".
    4. Pick a location and turn the VPN on.

connect-ios =
    🍏 <b>iPhone / iPad</b>

    1. Install Happ from the App Store.
    { connect-steps }

connect-android =
    🤖 <b>Android</b>

    1. Download and install Happ (the .apk file from the latest release).
    { connect-steps }

connect-windows =
    🪟 <b>Windows</b>

    1. Download and install Happ (the Windows installer from the latest release).
    { connect-steps }

connect-macos =
    💻 <b>macOS</b>

    1. Install Happ from the App Store.
    { connect-steps }
