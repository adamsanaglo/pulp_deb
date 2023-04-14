Name:		packages-microsoft-prod
Version:	1.1
Release:	1
Summary:	Configure clients for the Microsoft prod repo

Group:		Applications/Internet
License:	MIT
URL:		https://github.com/microsoft/linux-package-repositories
Source0:	repo.template
Source1:	LICENSE
BuildArch:	noarch
BuildRoot:  %{_topdir}/BUILD/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%description
Configure clients for the Microsoft prod repo

%prep

%build

%install
# Install the repo file
mkdir -p %{buildroot}/%{configroot}
%{_builddir}/repo_config.sh %{SOURCE0} %{buildroot}/%{configroot} microsoft-prod %{distro} %{release_version} prod Production

# And the license
mkdir -p %{buildroot}/usr/share/licenses/%{name}
install -m 644 %{SOURCE1} %{buildroot}/usr/share/licenses/%{name}/LICENSE

%clean
rm -rf %{buildroot}

%files
%attr(644,root,root) /usr/share/licenses/%{name}/LICENSE
%config(noreplace) %attr(644,root,root) /%{configroot}/microsoft-prod.repo

%changelog
* Tue Mar 28 2023 Stephen Herr <stephenherr@microsoft.com> - 1.1-1
- Relicense under MIT

* Fri Jan 20 2017 Stephen Zarkos <stephen.zarkos@microsoft.com> - 1.0-1
- Initial package to include repo configuration and GPG key