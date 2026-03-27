NPM ?= npm

.PHONY: install install-backend install-frontend lint test dev-backend dev-frontend clean

install:
	$(NPM) install
	$(NPM) --workspace backend install
	$(NPM) --workspace frontend install

install-backend:
	$(NPM) --workspace backend install

install-frontend:
	$(NPM) --workspace frontend install

lint:
	$(NPM) run lint --workspaces --if-present

test:
	$(NPM) run test --workspaces --if-present

dev-backend:
	$(NPM) --workspace backend run dev

dev-frontend:
	$(NPM) --workspace frontend run dev

clean:
	rm -rf node_modules backend/node_modules frontend/node_modules
