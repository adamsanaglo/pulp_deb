# Set these via override
#RELVER?=16.04
#DISTRO?=ubuntu
PACKAGE:=packages-microsoft-prod
VERSION=1.1-$(DISTRO)$(RELVER)
FAKEROOT=./data-root
DOCDIR=$(FAKEROOT)/usr/share/doc/$(PACKAGE)/
LINTIANOVERRIDES=$(FAKEROOT)/usr/share/lintian/overrides/$(PACKAGE)
DEB=$(PACKAGE)_$(VERSION)_all.deb
LISTDIR=$(FAKEROOT)/etc/apt/sources.list.d
LISTFILE=microsoft-prod.list
GPGDIR=$(FAKEROOT)/usr/share/keyrings
GPGFILE=microsoft-prod.gpg
VERIFYKEYDIR=$(FAKEROOT)/usr/share/debsig/keyrings/EB3E94ADBE1229CF
VERIFYPOLICYDIR=$(FAKEROOT)/etc/debsig/policies/EB3E94ADBE1229CF

package: $(DEB)

$(DEB): tarballs debian-binary $(LINTPROFILE)
	-rm -f $@
	ar rc $@ debian-binary control.tar.gz data.tar.gz
	lintian $(LINTOPTION) $@

$(DOCDIR):
	mkdir -p $@

$(DOCDIR)/changelog.Debian.gz: SOURCES/changelog $(DOCDIR)
	cat $< | sed 's/PACKAGENAME/$(PACKAGE)/g' | gzip -n -9 > $@

$(DOCDIR)/copyright: SOURCES/copyright $(DOCDIR)
	cp $< $@

$(DOCDIR)/$(GPGFILE): SOURCES/$(GPGFILE) $(DOCDIR)
	cp $< $@

$(DOCDIR)/microsoft.pol: SOURCES/microsoft.pol $(DOCDIR)
	cp $< $@

$(DOCDIR)/$(LISTFILE): SOURCES/$(LISTFILE) $(DOCDIR)
	cp $< $@

$(LINTIANOVERRIDES): SOURCES/lintian-overrides
	mkdir -p $(@D)
	cat $< | sed 's/PACKAGENAME/$(PACKAGE)/g' > $@

$(LINTPROFILE):
	mkdir -p $(LINTPROFILEDIR)
	cp main.profile $(LINTPROFILEDIR)

debian-binary:
	echo 2.0 > debian-binary

tarballs: data.tar.gz control.tar.gz

control.tar.gz: md5sums SOURCES/control
	-rm -rf control-root
	-mkdir -p control-root	
	install -m 644 SOURCES/conffiles SOURCES/control md5sums control-root
	install -m 755 SOURCES/preinst SOURCES/postinst SOURCES/prerm control-root
	sed -i '/^Version:/c Version: $(VERSION)' control-root/control
	sed -i '/^Package:/c Package: $(PACKAGE)' control-root/control
	cd control-root && tar -czf ../$@ --owner=root --group=root .

md5sums: install-deps
	(cd $(FAKEROOT) && md5sum `find -type f`) > $@
	chmod 0644 $@

data.tar.gz: install-deps \
             $(DOCDIR)/changelog.Debian.gz \
             $(DOCDIR)/copyright \
             $(DOCDIR)/$(GPGFILE) \
             $(DOCDIR)/microsoft.pol \
             $(DOCDIR)/$(LISTFILE) \
             $(LINTIANOVERRIDES)
	find $(FAKEROOT) -type d | xargs chmod 0755
	find $(FAKEROOT) -type d | xargs chmod ug-s
	find $(FAKEROOT)/usr/share/doc -type f | xargs chmod 0644
	find $(FAKEROOT)/usr/share/lintian -type f | xargs chmod 0644
	cd $(FAKEROOT) && tar -czf ../$@ --owner=root --group=root --mode=go-w *

.PHONY: clean install-clean install-deps $(LINTPROFILE)

clean: install-clean
	-rm -rf control-root
	-rm -f debian-binary *.tar.gz md5sums
	-rm -f packages-microsoft-*.deb

install-clean:
	-rm -rf $(FAKEROOT)

install-deps: install-clean	
	mkdir -p $(LISTDIR) $(GPGDIR) $(VERIFYKEYDIR) $(VERIFYPOLICYDIR)
	install -m 644 SOURCES/$(LISTFILE) $(LISTDIR)/$(LISTFILE)
	install -m 644 SOURCES/$(GPGFILE) $(GPGDIR)/$(GPGFILE)
	gpg -o - --dearmor $(GPGDIR)/$(GPGFILE) | install -m 644 /dev/stdin $(VERIFYKEYDIR)/microsoft.gpg
	install -m 644 SOURCES/microsoft.pol $(VERIFYPOLICYDIR)/microsoft.pol
