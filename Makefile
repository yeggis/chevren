.PHONY: aur-update release

VERSION := $(shell grep '^pkgver' PKGBUILD | cut -d= -f2)
PKGREL  := $(shell grep '^pkgrel' PKGBUILD | cut -d= -f2)

aur-update:
	git pull
	cp PKGBUILD .SRCINFO ../chevren-aur/
	cd ../chevren-aur && \
		git add PKGBUILD .SRCINFO && \
		git commit -m "chore: update AUR package to v$(VERSION)-$(PKGREL)" && \
		git push
