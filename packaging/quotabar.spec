%{!?quotabar_version:%global quotabar_version 0.4.1}

Name:           quotabar
Version:        %{quotabar_version}
Release:        1
Summary:        Claude and Codex subscription quotas in the GNOME panel
License:        MIT AND CC0-1.0
URL:            https://github.com/akkaz/quotabar
Source0:        https://github.com/akkaz/quotabar/releases/download/v%{version}/quotabar-%{version}-source.tar.gz
BuildArch:      noarch

BuildRequires:  python3
BuildRequires:  glib2
BuildRequires:  desktop-file-utils
Requires:       python3 >= 3.10
Requires:       gnome-shell >= 48
Requires:       gnome-shell < 52
Requires:       gjs
Requires:       gtk4 >= 4.10
Requires:       libadwaita >= 1.4
Requires:       glib2
Requires:       ptyxis
Requires:       hicolor-icon-theme
Requires:       zenity

%description
Native GNOME panel indicator with account-wide subscription usage, reset
countdowns, native preferences and account setup through official provider CLIs.
No telemetry, hosted backend, credentials or inference requests are included.
Requires user-installed Claude Code and/or Codex CLIs.

%prep
%setup -q -n quotabar-%{version}

%build
glib-compile-schemas --strict extension/schemas
desktop-file-validate packaging/quotabar.desktop

%install
extension=%{buildroot}%{_datadir}/gnome-shell/extensions/quotabar@akkaz.dev
mkdir -p "$extension/backend" %{buildroot}%{_bindir}
cp -a extension/. "$extension/"
cp -a quotabar "$extension/backend/"
find "$extension" -type d -name __pycache__ -prune -exec rm -rf {} +
chmod 755 "$extension/helper.py"
ln -s ../share/gnome-shell/extensions/quotabar@akkaz.dev/helper.py %{buildroot}%{_bindir}/quotabar
install -Dm644 packaging/quotabar.desktop %{buildroot}%{_datadir}/applications/quotabar.desktop
install -Dm644 packaging/quotabar.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/quotabar.svg
install -Dm644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
install -Dm644 extension/icons/LICENSE-CC0.txt %{buildroot}%{_licensedir}/%{name}/LICENSE-CC0.txt
install -Dm644 THIRD_PARTY_NOTICES.md %{buildroot}%{_docdir}/%{name}/THIRD_PARTY_NOTICES.md
install -Dm644 README.md %{buildroot}%{_docdir}/%{name}/README.md
install -Dm644 README.it.md %{buildroot}%{_docdir}/%{name}/README.it.md

%files
%license %{_licensedir}/%{name}/
%doc %{_docdir}/%{name}/
%{_bindir}/quotabar
%{_datadir}/gnome-shell/extensions/quotabar@akkaz.dev/
%{_datadir}/applications/quotabar.desktop
%{_datadir}/icons/hicolor/scalable/apps/quotabar.svg
