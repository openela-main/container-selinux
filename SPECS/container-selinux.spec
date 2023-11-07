%global debug_package   %{nil}

# container-selinux
%global git0 https://github.com/containers/container-selinux

# container-selinux stuff (prefix with ds_ for version/release etc.)
# Some bits borrowed from the openstack-selinux package
%global selinuxtype targeted
%global moduletype services
%global modulenames container

# Usage: _format var format
# Expand 'modulenames' into various formats as needed
# Format must contain '$x' somewhere to do anything useful
%global _format() export %1=""; for x in %{modulenames}; do %1+=%2; %1+=" "; done;

# Version of SELinux we were using
%global selinux_policyver 38.1.2-1.el9

Epoch: 3
Name: container-selinux
Version: 2.221.0
Release: 1%{?dist}
License: GPLv2
URL: %{git0}
Summary: SELinux policies for container runtimes
Source0: %{git0}/archive/v%{version}.tar.gz
BuildArch: noarch
BuildRequires: git
BuildRequires: pkgconfig(systemd)
BuildRequires: selinux-policy >= %{selinux_policyver}
BuildRequires: selinux-policy-devel >= %{selinux_policyver}
# RE: rhbz#1195804 - ensure min NVR for selinux-policy
Requires: selinux-policy >= %{selinux_policyver}
Requires(post): selinux-policy-base >= %{selinux_policyver}
Requires(post): selinux-policy-targeted >= %{selinux_policyver}
Requires(post): policycoreutils >= 2.5-11
%if 0%{?rhel} > 7 || 0%{?fedora}
Requires(post): policycoreutils-python-utils
%else
Requires(post): policycoreutils-python
%endif
Requires(post): libselinux-utils
Requires(post): sed
Obsoletes: %{name} <= 2:1.12.5-14
Obsoletes: docker-selinux <= 2:1.12.4-28
Provides: docker-selinux = %{epoch}:%{version}-%{release}
Provides: docker-engine-selinux = %{epoch}:%{version}-%{release}
Conflicts: udica < 0.2.6-1

%description
SELinux policy modules for use with container runtimes.

%prep
%autosetup -Sgit

# Remove some lines for RHEL 8 build
%if ! 0%{?fedora} && 0%{?rhel} <= 8
sed -i 's/watch watch_reads//' container.if
sed -i '/sysfs_t:dir watch/d' container.te
sed -i '/systemd_chat_resolved/d' container.te
%endif

sed -i 's/man: install-policy/man:/' Makefile
sed -i 's/install: man/install:/' Makefile

# https://github.com/containers/container-selinux/issues/203
%if 0%{?fedora} <= 37 || 0%{?rhel} <= 9
sed -i '/user_namespace/d' container.te
%endif

%build
make

%install
# install policy modules
%_format MODULES $x.pp.bz2
install -d %{buildroot}%{_datadir}/selinux/packages
install -d -p %{buildroot}%{_datadir}/selinux/devel/include/services
install -p -m 644 container.if %{buildroot}%{_datadir}/selinux/devel/include/services
install -m 0644 $MODULES %{buildroot}%{_datadir}/selinux/packages
install -d %{buildroot}/%{_datadir}/containers/selinux
install -m 644 container_contexts %{buildroot}/%{_datadir}/containers/selinux/contexts
install -d %{buildroot}%{_datadir}/udica/templates
install -m 0644 udica-templates/*.cil %{buildroot}%{_datadir}/udica/templates

# remove spec file
rm -rf %{name}.spec

%check

%pre
%selinux_relabel_pre -s %{selinuxtype}

%post
# Install all modules in a single transaction
if [ $1 -eq 1 ]; then
   %{_sbindir}/setsebool -P -N virt_use_nfs=1 virt_sandbox_use_all_caps=1
fi
%_format MODULES %{_datadir}/selinux/packages/$x.pp.bz2
%{_sbindir}/semodule -n -s %{selinuxtype} -r container 2> /dev/null
%{_sbindir}/semodule -n -s %{selinuxtype} -d docker 2> /dev/null
%{_sbindir}/semodule -n -s %{selinuxtype} -d gear 2> /dev/null
%selinux_modules_install -s %{selinuxtype} $MODULES
. %{_sysconfdir}/selinux/config
sed -e "\|container_file_t|h; \${x;s|container_file_t||;{g;t};a\\" -e "container_file_t" -e "}" -i /etc/selinux/${SELINUXTYPE}/contexts/customizable_types > /dev/null 2>&1
matchpathcon -qV %{_sharedstatedir}/containers || restorecon -R %{_sharedstatedir}/containers &> /dev/null || :

%postun
if [ $1 -eq 0 ]; then
%selinux_modules_uninstall -s %{selinuxtype} %{modulenames} docker
fi

%triggerpostun -- container-selinux < 3:2.162.1-3
if %{_sbindir}/selinuxenabled ; then
  echo "Fixing Rootless SELinux labels in homedir"
  %{_sbindir}/restorecon -R /home/*/.local/share/containers/storage/overlay*  2> /dev/null || :
fi

%posttrans
%selinux_relabel_post -s %{selinuxtype}

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%doc README.md
%{_datadir}/selinux/*
%dir %{_datadir}/containers/selinux
%{_datadir}/containers/selinux/contexts
%dir %{_datadir}/udica/templates/
%{_datadir}/udica/templates/*


%changelog
* Tue Aug 15 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.221.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.221.0
- Related: #2176063

* Mon Jul 03 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.219.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.219.0
- Related: #2176063

* Wed Jun 21 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.218.0-3
- rebuild
- Resolves: #2181174

* Wed Jun 21 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.218.0-2
- rebuild
- Resolves: #2214567
- Resolves: #2214569

* Thu Jun 08 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.218.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.218.0
- Related: #2176063

* Tue Jun 06 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.217.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.217.0
- Related: #2176063

* Fri Jun 02 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.216.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.216.0
- Related: #2176063

* Wed May 24 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.215.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.215.0
- Related: #2176063

* Mon May 15 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.213.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.213.0
- Related: #2176063

* Wed May 03 2023 Lokesh Mandvekar <lsm5@redhat.com> - 3:2.211.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.211.1
- Related: #2176063

* Mon Apr 24 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.211.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.211.0
- Related: #2176063

* Tue Apr 11 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.210.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.210.0
- Related: #2176063

* Mon Apr 03 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.209.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.209.0
- Related: #2176063

* Fri Mar 24 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.206.0-2
- use conditionals from https://github.com/containers/container-selinux/blob/main/container-selinux.spec.rpkg
- Related: #2176063

* Wed Mar 22 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.206.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.206.0
- Related: #2176063

* Mon Mar 20 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.205.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.205.0
- remove user_namespace class, thanks to Lokesh Mandvekar
- Resolves: #2178990

* Mon Jan 30 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.199.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.199.0
- Related: #2124478

* Fri Jan 06 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.198.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.198.0
- Related: #2124478

* Wed Jan 04 2023 Jindrich Novy <jnovy@redhat.com> - 3:2.197.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.197.0
- Related: #2124478

* Thu Dec 15 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.195.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.195.1
- Related: #2124478

* Mon Dec 05 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.193.0-2
- require at least selinux-policy-38.1.2-1.el9
- Resolves: #2150283

* Mon Nov 28 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.193.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.193.0
- Related: #2124478

* Mon Oct 31 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.191.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.191.0
- Related: #2124478

* Tue Oct 18 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.190.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.190.0
- Related: #2124478

* Fri Jul 15 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.189.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.189.0
- Related: #2061316

* Mon Jun 27 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.188.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.188.0
- Related: #2061316

* Wed May 25 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.187.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.187.0
- Related: #2061316

* Tue Apr 19 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.183.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.183.0
- Related: #2061316

* Thu Mar 24 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.181.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.181.0
- Related: #2061316

* Tue Mar 08 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.180.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.180.0
- Related: #2061316

* Mon Feb 28 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.179.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.179.1
- Related: #2000051

* Fri Feb 11 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.178.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.178.0
- Related: #2000051

* Thu Feb 10 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.177.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.177.0
- Related: #2000051

* Thu Feb 03 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.176.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.176.0
- Related: #2000051

* Wed Feb 02 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.174.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.174.0
- Related: #2000051

* Thu Jan 27 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.173.2-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.173.2
- Related: #2000051

* Fri Jan 21 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.173.1-2
- update minimal selinux_policy dependency
- Related: #2000051

* Wed Jan 19 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.173.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.173.1
- Related: #2000051

* Wed Jan 12 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.173.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.173.0
- Related: #2000051

* Fri Jan 07 2022 Jindrich Novy <jnovy@redhat.com> - 3:2.172.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.172.1
- Related: #2000051

* Tue Nov 23 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.172.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.172.0
- Related: #2000051

* Thu Nov 11 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.171.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.171.0
- Related: #2000051

* Wed Oct 06 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.170.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.170.0
- Related: #2000051

* Fri Oct 01 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.169.0-3
- perform only sanity/installability tests for now
- Related: #2000051

* Wed Sep 29 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.169.0-2
- add gating.yaml
- Related: #2000051

* Mon Sep 27 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.169.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.169.0
- Related: #2000051

* Tue Sep 21 2021 Vit Mojzis <vmojzis@redhat.com> - 2:2.168.0-2
- Start shipping udica templates
- Related: #2000051

* Tue Sep 14 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.168.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.168.0
- Related: #2000051

* Fri Sep 03 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.167.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.167.0
- Related: #2000051

* Mon Aug 09 2021 Mohan Boddu <mboddu@redhat.com> - 3:2.164.2-2
- Rebuilt for IMA sigs, glibc 2.34, aarch64 flags
  Related: rhbz#1991688

* Tue Aug 03 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.164.2-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.164.2
- Related: #1970747

* Mon Jul 19 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.164.1-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.164.1
- Related: #1970747

* Wed Jun 23 2021 Jindrich Novy <jnovy@redhat.com> - 3:2.163.0-2
- add trigger to fix labels in users homedirs, before overlayfs
  is supported by default for non root users
- Related: #1970747

* Mon Jun 14 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.163.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.163.0
- Related: #1970747

* Fri Jun 11 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.162.2-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.162.2

* Thu Apr 15 2021 Mohan Boddu <mboddu@redhat.com> - 2:2.160.0-2
- Rebuilt for RHEL 9 BETA on Apr 15th 2021. Related: rhbz#1947937

* Wed Mar 31 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.160.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.160.0

* Tue Mar 23 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.159.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.159.0

* Fri Feb 12 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.158.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.158.0

* Wed Jan 20 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.156.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.156.0

* Tue Jan 05 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.155.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.155.0

* Mon Jan 04 2021 Jindrich Novy <jnovy@redhat.com> - 2:2.154.0-0.2
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.154.0

* Sun Dec 20 2020 Petr Šabata <contyk@redhat.com> - 2:2.151.0-1.1
- Minor bump for gcc11

* Tue Nov 03 2020 Jindrich Novy <jnovy@redhat.com> - 2:2.151.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.151.0

* Fri Oct 23 2020 Jindrich Novy <jnovy@redhat.com> - 2:2.150.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.150.0

* Fri Sep 18 2020 Jindrich Novy <jnovy@redhat.com> - 2:2.145.0-1
- update to
  https://github.com/containers/container-selinux/releases/tag/v2.145.0

* Thu Sep 17 2020 Jindrich Novy <jnovy@redhat.com> - 2:2.144.0-2
- sync with rhel8-8.3.0

* Thu Sep 17 2020 Jindrich Novy <jnovy@redhat.com> - 2:2.144.0-1
- update to https://github.com/containers/container-selinux/releases/tag/v2.144.0
- Related: #1821193

* Fri Jun 14 2019 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.107-1
- Resolves: #1720654 - rebase to v2.107

* Tue Apr 30 2019 Eduardo Santiago <santiago@redhat.com> - 2:2.99-3.git9a53d6c
- strip away fs_manage_fusefs_* to resolve build-time error

* Tue Apr 23 2019 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:2.99-2.git9a53d6c
- rebase

* Mon Mar 11 2019 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.89-1.git2521d0d
- bump to v2.89

* Fri Mar 01 2019 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:2.87-3.git891a85f
- fix fersion number

* Fri Mar 01 2019 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:2.75-2.git891a85f
- rebase

* Tue Nov 13 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.75-1.git99e2cfd
- bump to v2.75
- built commit 99e2cfd

* Mon Oct 22 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.74-1
- Resolves: #1641655 - bump to v2.74
- built commit a62c2db

* Tue Sep 18 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:2.73-3
- tweak macro for fedora - applies to rhel8 as well

* Mon Sep 17 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:2.73-2
- moved changelog entries:
- Define spc_t as a container_domain, so that container_runtime will transition
to spc_t even when setup with nosuid.
- Allow container_runtimes to setattr on callers fifo_files
- Fix restorecon to not error on missing directory

* Thu Sep 6 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.69-3
- Make sure we pull in the latest selinux-policy

* Wed Jul 25 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.69-2
- Add map support to container-selinux for RHEL 7.5
- Dontudit attempts to write to kernel_sysctl_t

* Mon Jul 16 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.68-1
- Add label for /var/lib/origin
- Add customizable_file_t to customizable_types

* Sun Jul 15 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.67-1
- Add policy for container_logreader_t

* Thu Jun 14 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.66-1
- Allow dnsmasq to dbus chat with spc_t

* Sun Jun 3 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.64-1
- Allow containers to create all socket classes

* Thu May 24 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.62-1
- Label overlay directories under /var/lib/containers/ correctly

* Mon May 21 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.61-1
- Allow spc_t to load kernel modules from inside of container 

* Mon May 21 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.60-1
- Allow containers to list cgroup directories
- Transition for unconfined_service_t to container_runtime_t when executing container_runtime_exec_t.

* Mon May 21 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.58-2
- Run restorecon /usr/bin/podman in postinstall

* Fri May 18 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.58-1
- Add labels to allow podman to be run from a systemd unit file

* Mon May 7 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.57-1
- Set the version of SELinux policy required to the latest to fix build issues.

* Wed Apr 11 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.56-1
- Allow container_runtime_t to transition to spc_t over unlabeled files

* Mon Mar 26 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.55-1
    Allow iptables to read container state
    Dontaudit attempts from containers to write to /proc/self
    Allow spc_t to change attributes on container_runtime_t fifo files

* Thu Mar 8 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.52-1
- Add better support for writing custom selinux policy for customer container domains.

* Thu Mar 8 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.51-1
- Allow shell_exec_t as a container_runtime_t entrypoint

* Wed Mar 7 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.50-1
- Allow bin_t as a container_runtime_t entrypoint

* Fri Mar 2 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.49-1
- Add support for MLS running container runtimes
- Add missing allow rules for running systemd in a container

* Wed Feb 21 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.48-1
- Update policy to match master branch
- Remove typebounds and replace with nnp_transition and nosuid_transition calls

* Tue Jan 9 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.41-1
- Add support to nnp_transition for container domains
- Eliminates need for typebounds.

* Tue Jan 9 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.40-1
- Allow container_runtime_t to use user ttys
- Fixes bounds check for container_t

* Mon Jan 8 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.39-1
- Allow container runtimes to use interited terminals.  This helps
satisfy the bounds check of container_t versus container_runtime_t.

* Sat Jan 6 2018 Dan Walsh <dwalsh@fedoraproject.org> - 2.38-1
- Allow container runtimes to mmap container_file_t devices
- Add labeling for rhel push plugin

* Tue Dec 12 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.37-1
- Allow containers to use inherited ttys
- Allow ostree to handle labels under /var/lib/containers/ostree

* Mon Nov 27 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.36-1
- Allow containers to relabelto/from all file types to container_file_t

* Mon Nov 27 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.35-1
- Allow container to map chr_files labeled container_file_t

* Wed Nov 22 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.34-1
- Dontaudit container processes getattr on kernel file systems

* Sun Nov 19 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.33-1
- Allow containers to read /etc/resolv.conf and /etc/hosts if volume
- mounted into container.

* Wed Nov 8 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.32-1
- Make sure users creating content in /var/lib with right labels

* Thu Oct 26 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.31-1
- Allow the container runtime to dbus chat with dnsmasq
- add dontaudit rules for container trying to write to /proc

* Tue Oct 10 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.29-1
- Add support for lxcd
- Add support for labeling of tmpfs storage created within a container.

* Mon Oct 9 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.28-1
- Allow a container to umount a container_file_t filesystem

* Fri Sep 22 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.27-1
-  Allow container runtimes to work with the netfilter sockets
-  Allow container_file_t to be an entrypoint for VM's
-  Allow spc_t domains to transition to svirt_t

* Fri Sep 22 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.24-1
-     Make sure container_runtime_t has all access of container_t

* Thu Sep 7 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.23-1
- Allow container runtimes to create sockets in tmp dirs

* Tue Sep 5 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.22-1
- Add additonal support for crio labeling.

* Mon Aug 14 2017 Troy Dawson <tdawson@redhat.com> - 2.21-3
- Fixup spec file conditionals

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2:2.21-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jul 6 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.21-1
- Allow containers to execmod on container_share_t files.

* Thu Jul 6 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.20-2
- Relabel runc and crio executables

* Fri Jun 30 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2.20-1
- Allow container processes to getsession

* Wed Jun 14 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.19-2.1
- update release tag to isolate from 7.3

* Wed Jun 14 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2:2.19-1
- Fix mcs transition problem on stdin/stdout/stderr
- Add labels for CRI-O
- Allow containers to use tunnel sockets

* Tue Jun 06 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.15-1.1
- Resolves: #1451289
- rebase to v2.15
- built @origin/RHEL-1.12 commit 583ca40

* Mon Mar 20 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2:2.10-2.1
- Make sure we have a late enough version of policycoreutils

* Mon Mar 6 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2:2.10-1
- Update to the latest container-selinux patch from upstream
- Label files under /usr/libexec/lxc as container_runtime_exec_t
- Give container_t access to XFRM sockets
- Allow spc_t to dbus chat with init system
- Allow containers to read cgroup configuration mounted into a container

* Tue Feb 21 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.9-4
- Resolves: #1425574
- built commit 79a6d70

* Mon Feb 20 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.9-3
- Resolves: #1420591
- built @origin/RHEL-1.12 commit 8f876c4

* Mon Feb 13 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.9-2
- built @origin/RHEL-1.12 commit 33cb78b

* Fri Feb 10 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.8-2
-

* Tue Feb 07 2017 Lokesh Mandvekar <lsm5@redhat.com> - 2:2.7-1
- built origin/RHEL-1.12 commit 21dd37b

* Fri Jan 20 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.4-2
- correct version-release in changelog entries

* Thu Jan 19 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2:2.4-1
- Add typebounds statement for container_t from container_runtime_t
- We should only label runc not runc*

* Tue Jan 17 2017 Dan Walsh <dwalsh@fedoraproject.org> - 2:2.3-1
- Fix labeling on /usr/bin/runc.*
- Add sandbox_net_domain access to container.te
- Remove containers ability to look at /etc content

* Wed Jan 11 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.2-4
- use upstream's RHEL-1.12 branch, commit 56c32da for CentOS 7

* Tue Jan 10 2017 Jonathan Lebon <jlebon@redhat.com> - 2:2.2-3
- properly disable docker module in %%post

* Sat Jan 07 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.2-2
- depend on selinux-policy-targeted
- relabel docker-latest* files as well

* Fri Jan 06 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.2-1
- bump to v2.2
- additional labeling for ocid

* Fri Jan 06 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.0-2
- install policy at level 200
- From: Dan Walsh <dwalsh@redhat.com>

* Fri Jan 06 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:2.0-1
- Resolves: #1406517 - bump to v2.0 (first upload to Fedora as a
standalone package)
- include projectatomic/RHEL-1.12 branch commit for building on centos/rhel

* Mon Dec 19 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.12.4-29
- new package (separated from docker)
