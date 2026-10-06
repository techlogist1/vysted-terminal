# Licensing — plain words

Vysted Terminal is **source-available**, not open-source. Here's what that means in
practice.

## What you can do without asking

- Download the source, install it, and run it.
- Use it for any noncommercial purpose — personal use, research, study, hobby
  projects, education, and use by nonprofits, schools, and government bodies.

This is the grant under the public license, **PolyForm Strict 1.0.0** (see
[`LICENSE`](./LICENSE)).

## What needs the commercial license

Anything beyond that noncommercial grant needs a commercial license
(see [`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md)):

- Any commercial use, by an individual or an organization.
- Any modification of the software, or building a derivative work from it.
- Any redistribution — of the original software or a modified version, closed-source
  or otherwise.

If none of the above apply to you, PolyForm Strict already covers you and you don't
need to contact anyone.

## Every commit before the relicensing commit stays AGPL-3.0

This is a hard rule, not a courtesy: **every commit made before the relicensing
commit remains available under its original AGPL-3.0 license.** Relicensing only
changes the terms for new work going forward — it does not and cannot revoke the
AGPL-3.0 grant already given on the history that came before it.

## Contact

Commercial licensing inquiries: **commercial@vysted.com** _(placeholder address —
to be confirmed at launch)._

## The Apache-2.0 carve-out for plugin authors

So third-party plugin authors are never blocked by the core's license, the plugin
contract and the bundled example plugin are separately licensed under
**Apache-2.0** (see [`LICENSE-APACHE`](./LICENSE-APACHE)):

- `types/plugin.ts` — the `VystedPlugin` contract
- `types/plugin-runtime.ts` — the runtime types the contract depends on
- `plugins/example/index.ts` — the example plugin
- `plugins/example/example.test.ts` — the example plugin's tests
- `plugins/example/manifest.json` — the example plugin's manifest (JSON files
  don't carry a header comment, so it's listed here instead)

A plugin you write that only imports these files is Apache-2.0 territory — you are
not bound by PolyForm Strict or the commercial license for your own plugin code.

---

_This page is a summary, not legal advice; the license texts govern._
