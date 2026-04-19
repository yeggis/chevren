.PHONY: aur-update release

VERSION := $(shell grep '^pkgver' PKGBUILD | cut -d= -f2)
PKGREL  := $(shell grep '^pkgrel' PKGBUILD | cut -d= -f2)

aur-update:
	updpkgsums
	git add PKGBUILD
	git diff --cached --quiet || git commit -m "chore: update sha256sums"
	git pull --rebase
	makepkg --printsrcinfo > .SRCINFO
	cp PKGBUILD .SRCINFO ../chevren-aur/
	cd ../chevren-aur && \
		git add PKGBUILD .SRCINFO && \
		git commit -m "chore: update AUR package to v$(VERSION)-$(PKGREL)" || true && \
		git push

release:
	rm -f dist/chevren-extension.zip dist/chevren-extension-firefox.zip dist/chevren-extension-chrome.zip
	mkdir -p dist
	cd extension && zip -r ../dist/chevren-extension-firefox.zip . -x "*.zip"
	cd extension && \
		tmp=$$(mktemp -d) && \
		cp -r . $$tmp/ && \
		cd $$tmp && \
		node -e "const fs=require('fs');const m=JSON.parse(fs.readFileSync('manifest.json'));delete m.background.scripts;fs.writeFileSync('manifest.json',JSON.stringify(m,null,2));" && \
		zip -r $(CURDIR)/dist/chevren-extension-chrome.zip . -x "*.zip" && \
		rm -rf $$tmp
	cp dist/chevren-extension-firefox.zip dist/chevren-extension.zip
	@echo "dist/chevren-extension-firefox.zip (AMO) hazır"
	@echo "dist/chevren-extension-chrome.zip (Chrome/manuel) hazır"
	@echo "dist/chevren-extension.zip hazır"
