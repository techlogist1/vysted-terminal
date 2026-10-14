<!-- DRAFT at 3412caf5840f2c36a33042852f9066a7dddc7ddf by the R15 notices agent; promote per DECISIONS §5.1 -->

# Third-party notices (draft)

Vysted Terminal itself is licensed PolyForm Strict 1.0.0 (the plugin contract and the example plugin are separately Apache-2.0). It bundles the third-party components listed below, each under its own licence, as separate programs or processes where noted.

Counts by bundle (bundled/runtime packages only, dev-only and build-only excluded): cargo: 542; npm: 205; vysted-openbb-mcp-sidecar: 106; vysted-sec-edgar-mcp-sidecar: 68; vysted-sidecar: 125. Total copyleft rows: 22.

## Section A — Copyleft components

| Package | Version | Binary | Licence | Process boundary | Corresponding source |
|---|---|---|---|---|---|
| cssparser | 0.36.0 | src-tauri (desktop core) | MPL-2.0 | compiled unmodified into the desktop core binary | upstream https://github.com/servo/rust-cssparser; pinned in this repo's requirements/lock file for src-tauri (desktop core). licence text: see upstream https://github.com/servo/rust-cssparser (this package ships no local LICENSE file) |
| cssparser-macros | 0.6.1 | src-tauri (desktop core) | MPL-2.0 | compiled unmodified into the desktop core binary | upstream https://github.com/servo/rust-cssparser; pinned in this repo's requirements/lock file for src-tauri (desktop core). licence text: see upstream https://github.com/servo/rust-cssparser (this package ships no local LICENSE file) |
| dtoa-short | 0.3.5 | src-tauri (desktop core) | MPL-2.0 | compiled unmodified into the desktop core binary | upstream https://github.com/upsuper/dtoa-short; pinned in this repo's requirements/lock file for src-tauri (desktop core). licence text: see upstream https://github.com/upsuper/dtoa-short (this package ships no local LICENSE file) |
| option-ext | 0.2.0 | src-tauri (desktop core) | MPL-2.0 | compiled unmodified into the desktop core binary | upstream https://github.com/soc/option-ext.git; pinned in this repo's requirements/lock file for src-tauri (desktop core). licence text: see upstream https://github.com/soc/option-ext.git (this package ships no local LICENSE file) |
| selectors | 0.36.1 | src-tauri (desktop core) | MPL-2.0 | compiled unmodified into the desktop core binary | upstream https://github.com/servo/stylo; pinned in this repo's requirements/lock file for src-tauri (desktop core). licence text: see upstream https://github.com/servo/stylo (this package ships no local LICENSE file) |
| certifi | 2026.5.20 | vysted-openbb-mcp-sidecar | Mozilla Public License 2.0 (MPL 2.0) | spawned as a separate process over loopback MCP, unmodified | upstream https://github.com/certifi/python-certifi; pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: the package's own LICENSE file in vysted-openbb-mcp-sidecar's venv, or upstream https://github.com/certifi/python-certifi (only AGPL-3.0/GPL-2.0/LGPL-3.0 texts are carried in the Appendix) |
| frozendict | 2.4.7 | vysted-openbb-mcp-sidecar | GNU Lesser General Public License v3 (LGPLv3) | spawned as a separate process over loopback MCP, unmodified | upstream https://github.com/Marco-Sulla/python-frozendict; pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (LGPL-3.0) |
| openbb-core | 1.6.9 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-economy | 1.6.1 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-equity | 1.6.1 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-fmp | 1.6.0 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-fred | 1.6.0 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-mcp-server | 1.4.0 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream Documentation, https://docs.openbb.co; pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-news | 1.6.0 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| openbb-yfinance | 1.6.2 | vysted-openbb-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-openbb-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| certifi | 2026.5.20 | vysted-sec-edgar-mcp-sidecar | Mozilla Public License 2.0 (MPL 2.0) | spawned as a separate process over loopback MCP, unmodified | upstream https://github.com/certifi/python-certifi; pinned in this repo's requirements/lock file for vysted-sec-edgar-mcp-sidecar. licence text: the package's own LICENSE file in vysted-sec-edgar-mcp-sidecar's venv, or upstream https://github.com/certifi/python-certifi (only AGPL-3.0/GPL-2.0/LGPL-3.0 texts are carried in the Appendix) |
| sec-edgar-mcp | 1.0.8 | vysted-sec-edgar-mcp-sidecar | GNU Affero General Public License v3 | spawned as a separate process over loopback MCP, unmodified | upstream Homepage, https://github.com/stefanoamorelli/sec-edgar-mcp; pinned in this repo's requirements/lock file for vysted-sec-edgar-mcp-sidecar. licence text: Appendix below (AGPL-3.0) |
| tqdm | 4.67.3 | vysted-sec-edgar-mcp-sidecar | MPL-2.0 AND MIT | spawned as a separate process over loopback MCP, unmodified | upstream homepage, https://tqdm.github.io; pinned in this repo's requirements/lock file for vysted-sec-edgar-mcp-sidecar. licence text: see upstream homepage, https://tqdm.github.io (this package ships no local LICENSE file) |
| Unidecode | 1.4.0 | vysted-sec-edgar-mcp-sidecar | GNU General Public License v2 or later (GPLv2+) | spawned as a separate process over loopback MCP, unmodified | upstream (URL not recorded); pinned in this repo's requirements/lock file for vysted-sec-edgar-mcp-sidecar. licence text: Appendix below (GPL-2.0) |
| certifi | 2026.5.20 | vysted-sidecar | Mozilla Public License 2.0 (MPL 2.0) | runs in-process inside the main sidecar binary, unmodified | upstream https://github.com/certifi/python-certifi; pinned in this repo's requirements/lock file for vysted-sidecar. licence text: the package's own LICENSE file in vysted-sidecar's venv, or upstream https://github.com/certifi/python-certifi (only AGPL-3.0/GPL-2.0/LGPL-3.0 texts are carried in the Appendix) |
| frozendict | 2.4.7 | vysted-sidecar | GNU Lesser General Public License v3 (LGPLv3) | runs in-process inside the main sidecar binary, unmodified | upstream https://github.com/Marco-Sulla/python-frozendict; pinned in this repo's requirements/lock file for vysted-sidecar. licence text: Appendix below (LGPL-3.0) |
| tqdm | 4.67.3 | vysted-sidecar | MPL-2.0 AND MIT | runs in-process inside the main sidecar binary, unmodified | upstream homepage, https://tqdm.github.io; pinned in this repo's requirements/lock file for vysted-sidecar. licence text: see upstream homepage, https://tqdm.github.io (this package ships no local LICENSE file) |

## Section B — Permissive components

### Python — vysted-sidecar

| Name | Version | Licence | URL |
|---|---|---|---|
| aiodns | 4.0.4 | MIT | repository, https://github.com/aio-libs/aiodns.git |
| aiofile | 3.11.1 | Apache-2.0 | Homepage, https://github.com/mosquito/aiofile |
| aiohappyeyeballs | 2.6.2 | Python Software Foundation License | Bug Tracker, https://github.com/aio-libs/aiohappyeyeballs/issues |
| aiohttp | 3.13.5 | MIT | Homepage, https://github.com/aio-libs/aiohttp |
| aiosignal | 1.4.0 | Apache Software License | https://github.com/aio-libs/aiosignal |
| annotated-doc | 0.0.4 | MIT | Homepage, https://github.com/fastapi/annotated-doc |
| annotated-types | 0.7.0 | MIT License | Homepage, https://github.com/annotated-types/annotated-types |
| anthropic | 0.100.0 | MIT License | Homepage, https://github.com/anthropics/anthropic-sdk-python |
| anyio | 4.13.0 | MIT | Documentation, https://anyio.readthedocs.io/en/latest/ |
| appdirs | 1.4.4 | MIT License | http://github.com/ActiveState/appdirs |
| attrs | 26.1.0 | MIT | Documentation, https://www.attrs.org/ |
| Authlib | 1.7.2 | BSD License | Documentation, https://docs.authlib.org/ |
| beartype | 0.22.9 | MIT | Docs, https://beartype.readthedocs.io |
| beautifulsoup4 | 4.14.3 | MIT License | Download, https://www.crummy.com/software/BeautifulSoup/bs4/download/ |
| brotli | 1.2.0 | MIT | https://github.com/google/brotli |
| cachetools | 6.2.6 | MIT | Homepage, https://github.com/tkem/cachetools/ |
| caio | 0.9.25 | Apache-2.0 | Source Code, https://github.com/mosquito/caio/ |
| ccxt | 4.5.53 | MIT License | https://ccxt.com |
| cffi | 2.0.0 | MIT | Documentation, https://cffi.readthedocs.io/ |
| charset-normalizer | 3.4.7 | MIT | Changelog, https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md |
| click | 8.4.0 | BSD-3-Clause | Changes, https://click.palletsprojects.com/page/changes/ |
| coincurve | 21.0.0 | MIT OR Apache-2.0 | Homepage, https://ofek.dev/coincurve/ |
| cryptography | 48.0.0 | Apache-2.0 OR BSD-3-Clause | changelog, https://cryptography.io/en/latest/changelog/ |
| curl_cffi | 0.15.0 | MIT | repository, https://github.com/lexiforest/curl_cffi |
| cyclopts | 4.15.0 | Apache-2.0 | Homepage, https://github.com/BrianPugh/cyclopts |
| distro | 1.9.0 | Apache Software License | https://github.com/python-distro/distro |
| dnspython | 2.8.0 | ISC License (ISCL) | homepage, https://www.dnspython.org |
| docstring_parser | 0.18.0 | MIT License | homepage, https://github.com/rr-/docstring_parser |
| ecbdata | 0.1.1 | MIT License | https://github.com/LucaMingarelli/ecbdata |
| email-validator | 2.3.0 | The Unlicense (Unlicense) | https://github.com/JoshData/python-email-validator |
| exceptiongroup | 1.3.1 | MIT License | Changelog, https://github.com/agronholm/exceptiongroup/blob/main/CHANGES.rst |
| fastapi | 0.136.1 | MIT | Homepage, https://github.com/fastapi/fastapi |
| fastmcp | 3.2.4 | Apache-2.0 | Homepage, https://gofastmcp.com |
| feedparser | 6.0.12 | BSD License | https://github.com/kurtmckee/feedparser |
| fredapi | 0.5.2 | Apache-2.0 | https://github.com/mortada/fredapi |
| frozenlist | 1.8.0 | Apache-2.0 | https://github.com/aio-libs/frozenlist |
| google-auth | 2.53.0 | Apache Software License | https://github.com/googleapis/google-auth-library-python |
| google-genai | 2.5.0 | Apache-2.0 | Homepage, https://github.com/googleapis/python-genai |
| griffelib | 2.0.2 | ISC |  |
| groq | 1.1.1 | Apache Software License | Homepage, https://github.com/groq/groq-python |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| httpcore | 1.0.9 | BSD-3-Clause | Documentation, https://www.encode.io/httpcore |
| httptools | 0.7.1 | MIT | Homepage, https://github.com/MagicStack/httptools |
| httpx | 0.28.1 | BSD License | Changelog, https://github.com/encode/httpx/blob/master/CHANGELOG.md |
| httpx-sse | 0.4.3 | MIT | Homepage, https://github.com/florimondmanca/httpx-sse |
| idna | 3.15 | BSD-3-Clause | Changelog, https://github.com/kjd/idna/blob/master/HISTORY.md |
| jaraco.classes | 3.4.0 | MIT License | https://github.com/jaraco/jaraco.classes |
| jaraco.context | 6.1.2 | MIT | Source, https://github.com/jaraco/jaraco.context |
| jaraco.functools | 4.5.0 | MIT | Source, https://github.com/jaraco/jaraco.functools |
| jiter | 0.15.0 | MIT |  |
| joserfc | 1.6.5 | BSD License | Documentation, https://jose.authlib.org/ |
| jsonref | 1.1.0 | MIT | documentation, https://jsonref.readthedocs.io/en/latest/ |
| jsonschema | 4.26.0 | MIT | Homepage, https://github.com/python-jsonschema/jsonschema |
| jsonschema-path | 0.5.0 | Apache Software License | Repository, https://github.com/p1c2u/jsonschema-path |
| jsonschema-specifications | 2025.9.1 | MIT | Documentation, https://jsonschema-specifications.readthedocs.io/ |
| jugaad-data | 0.33.1 | YOLO | Homepage, https://marketsetup.in/documentation/jugaad-data/ |
| keyring | 25.7.0 | MIT | Source, https://github.com/jaraco/keyring |
| lxml | 6.1.1 | BSD-3-Clause | https://lxml.de/ |
| markdown-it-py | 4.2.0 | MIT License | Documentation, https://markdown-it-py.readthedocs.io |
| mcp | 1.27.1 | MIT License | Homepage, https://modelcontextprotocol.io |
| mdurl | 0.1.2 | MIT License | Homepage, https://github.com/executablebooks/mdurl |
| more-itertools | 11.0.2 | MIT | Documentation, https://more-itertools.readthedocs.io/en/stable/ |
| multidict | 6.7.1 | Apache License 2.0 | https://github.com/aio-libs/multidict |
| multitasking | 0.0.13 | Apache Software License | https://github.com/ranaroussi/multitasking |
| numpy | 2.4.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | homepage, https://numpy.org |
| ollama | 0.6.2 | MIT | homepage, https://ollama.com |
| openai | 2.36.0 | Apache Software License | Homepage, https://github.com/openai/openai-python |
| openapi-pydantic | 0.5.1 | MIT License | https://github.com/mike-oakley/openapi-pydantic |
| opentelemetry-api | 1.42.1 | Apache-2.0 | Homepage, https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | Documentation, https://packaging.pypa.io/ |
| pandas | 3.0.3 | Apache-2.0 |  |
| pathable | 0.6.0 | Apache Software License | Repository, https://github.com/p1c2u/pathable |
| peewee | 4.0.6 | MIT | Repository, https://github.com/coleifer/peewee |
| platformdirs | 4.9.6 | MIT | Changelog, https://platformdirs.readthedocs.io/en/latest/changelog.html |
| propcache | 0.5.2 | Apache Software License | https://github.com/aio-libs/propcache |
| protobuf | 7.35.0 | BSD-3-Clause | https://developers.google.com/protocol-buffers/ |
| py-key-value-aio | 0.4.4 | Apache Software License |  |
| pyasn1 | 0.6.3 | BSD-3-Clause | Homepage, https://github.com/pyasn1/pyasn1 |
| pyasn1_modules | 0.4.2 | BSD License | https://github.com/pyasn1/pyasn1-modules |
| pycares | 5.0.1 | MIT | Homepage, http://github.com/saghul/pycares |
| pycparser | 3.0 | BSD-3-Clause | Homepage, https://github.com/eliben/pycparser |
| pydantic | 2.13.4 | MIT | Homepage, https://github.com/pydantic/pydantic |
| pydantic_core | 2.46.4 | MIT | Funding, https://github.com/sponsors/samuelcolvin |
| pydantic-settings | 2.14.1 | MIT | Homepage, https://github.com/pydantic/pydantic-settings |
| Pygments | 2.20.0 | BSD-2-Clause | Homepage, https://pygments.org |
| PyInstaller-bootloader | embedded | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | https://pyinstaller.org/ |
| PyJWT | 2.12.1 | MIT | Homepage, https://github.com/jpadilla/pyjwt |
| pypdf | 6.13.1 | BSD-3-Clause | Bug Reports, https://github.com/py-pdf/pypdf/issues |
| pyperclip | 1.11.0 | BSD License | Homepage, https://github.com/asweigart/pyperclip |
| python-dateutil | 2.9.0.post0 | BSD License | https://github.com/dateutil/dateutil |
| python-dotenv | 1.2.2 | BSD-3-Clause | Source, https://github.com/theskumar/python-dotenv |
| python-multipart | 0.0.29 | Apache-2.0 | Homepage, https://github.com/Kludex/python-multipart |
| pytz | 2026.2 | MIT License | http://pythonhosted.org/pytz |
| PyYAML | 6.0.3 | MIT License | https://pyyaml.org/ |
| QuantLib | 1.42.1 | BSD-3-Clause | https://www.quantlib.org |
| referencing | 0.37.0 | MIT | Documentation, https://referencing.readthedocs.io/ |
| requests | 2.34.2 | Apache Software License | Documentation, https://requests.readthedocs.io |
| rich | 14.3.4 | MIT License | Documentation, https://rich.readthedocs.io/en/latest/ |
| rich-rst | 2.0.1 | MIT | Bug Tracker, https://github.com/wasi-master/rich-rst/issues |
| rpds-py | 0.30.0 | MIT | Documentation, https://rpds.readthedocs.io/ |
| sdmx1 | 2.26.0 | Apache Software License | Homepage, https://github.com/khaeru/sdmx |
| setuptools | 82.0.1 | MIT | Source, https://github.com/pypa/setuptools |
| sgmllib3k | 1.0.0 | BSD License | http://hg.hardcoded.net/sgmllib |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| sniffio | 1.3.1 | MIT License | Homepage, https://github.com/python-trio/sniffio |
| soupsieve | 2.8.3 | MIT | Homepage, https://github.com/facelessuser/soupsieve |
| sse-starlette | 3.4.4 | BSD-3-Clause | Homepage, https://github.com/sysid/sse-starlette |
| starlette | 1.0.0 | BSD-3-Clause | Homepage, https://github.com/Kludex/starlette |
| tabulate | 0.10.0 | MIT | Homepage, https://github.com/astanin/python-tabulate |
| tenacity | 9.1.4 | Apache Software License | https://github.com/jd/tenacity |
| typing_extensions | 4.15.0 | PSF-2.0 | Bug Tracker, https://github.com/python/typing_extensions/issues |
| typing-inspection | 0.4.2 | MIT | Homepage, https://github.com/pydantic/typing-inspection |
| uncalled-for | 0.3.2 | MIT | Repository, https://github.com/chrisguidry/uncalled-for |
| urllib3 | 2.7.0 | MIT | Changelog, https://github.com/urllib3/urllib3/blob/main/CHANGES.rst |
| uvicorn | 0.46.0 | BSD-3-Clause | Changelog, https://uvicorn.dev/release-notes |
| uvloop | 0.22.1 | Apache Software License | github, https://github.com/MagicStack/uvloop |
| vaderSentiment | 3.3.2 | MIT | https://github.com/cjhutto/vaderSentiment |
| watchfiles | 1.2.0 | MIT License | Changelog, https://github.com/samuelcolvin/watchfiles/releases |
| wbgapi | 1.0.14 | MIT | https://github.com/tgherzog/wbgapi |
| websockets | 15.0.1 | BSD License | Homepage, https://github.com/python-websockets/websockets |
| yarl | 1.24.2 | Apache-2.0 | https://github.com/aio-libs/yarl |
| yfinance | 1.3.0 | Apache Software License | https://github.com/ranaroussi/yfinance |

### Python — vysted-openbb-mcp-sidecar

| Name | Version | Licence | URL |
|---|---|---|---|
| aiofile | 3.11.1 | Apache-2.0 | Homepage, https://github.com/mosquito/aiofile |
| aiohappyeyeballs | 2.6.2 | Python Software Foundation License | Bug Tracker, https://github.com/aio-libs/aiohappyeyeballs/issues |
| aiohttp | 3.13.5 | MIT | Homepage, https://github.com/aio-libs/aiohttp |
| aiosignal | 1.4.0 | Apache Software License | https://github.com/aio-libs/aiosignal |
| annotated-doc | 0.0.4 | MIT | Homepage, https://github.com/fastapi/annotated-doc |
| annotated-types | 0.7.0 | MIT License | Homepage, https://github.com/annotated-types/annotated-types |
| anyio | 4.13.0 | MIT | Documentation, https://anyio.readthedocs.io/en/latest/ |
| attrs | 26.1.0 | MIT | Documentation, https://www.attrs.org/ |
| Authlib | 1.7.2 | BSD License | Documentation, https://docs.authlib.org/ |
| beartype | 0.22.9 | MIT | Docs, https://beartype.readthedocs.io |
| beautifulsoup4 | 4.14.3 | MIT License | Download, https://www.crummy.com/software/BeautifulSoup/bs4/download/ |
| cachetools | 7.1.3 | MIT | Homepage, https://github.com/tkem/cachetools/ |
| caio | 0.9.25 | Apache-2.0 | Source Code, https://github.com/mosquito/caio/ |
| cffi | 2.0.0 | MIT | Documentation, https://cffi.readthedocs.io/ |
| charset-normalizer | 3.4.7 | MIT | Changelog, https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md |
| click | 8.4.0 | BSD-3-Clause | Changes, https://click.palletsprojects.com/page/changes/ |
| cryptography | 48.0.0 | Apache-2.0 OR BSD-3-Clause | changelog, https://cryptography.io/en/latest/changelog/ |
| curl_cffi | 0.15.0 | MIT | repository, https://github.com/lexiforest/curl_cffi |
| cyclopts | 4.15.0 | Apache-2.0 | Homepage, https://github.com/BrianPugh/cyclopts |
| dnspython | 2.8.0 | ISC License (ISCL) | homepage, https://www.dnspython.org |
| docstring_parser | 0.18.0 | MIT License | homepage, https://github.com/rr-/docstring_parser |
| email-validator | 2.3.0 | The Unlicense (Unlicense) | https://github.com/JoshData/python-email-validator |
| exceptiongroup | 1.3.1 | MIT License | Changelog, https://github.com/agronholm/exceptiongroup/blob/main/CHANGES.rst |
| fastapi | 0.128.8 | MIT | Homepage, https://github.com/fastapi/fastapi |
| fastmcp | 3.3.1 | Apache-2.0 | Homepage, https://gofastmcp.com |
| fastmcp-slim | 3.3.1 | Apache-2.0 | Homepage, https://gofastmcp.com |
| frozenlist | 1.8.0 | Apache-2.0 | https://github.com/aio-libs/frozenlist |
| griffelib | 2.0.2 | ISC |  |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| html5lib | 1.1 | MIT License | https://github.com/html5lib/html5lib-python |
| httpcore | 1.0.9 | BSD-3-Clause | Documentation, https://www.encode.io/httpcore |
| httpx | 0.28.1 | BSD License | Changelog, https://github.com/encode/httpx/blob/master/CHANGELOG.md |
| httpx-sse | 0.4.3 | MIT | Homepage, https://github.com/florimondmanca/httpx-sse |
| idna | 3.15 | BSD-3-Clause | Changelog, https://github.com/kjd/idna/blob/master/HISTORY.md |
| importlib_metadata | 9.0.0 | Apache-2.0 | Source, https://github.com/python/importlib_metadata |
| jaraco.classes | 3.4.0 | MIT License | https://github.com/jaraco/jaraco.classes |
| jaraco.context | 6.1.2 | MIT | Source, https://github.com/jaraco/jaraco.context |
| jaraco.functools | 4.5.0 | MIT | Source, https://github.com/jaraco/jaraco.functools |
| joserfc | 1.6.5 | BSD License | Documentation, https://jose.authlib.org/ |
| jsonref | 1.1.0 | MIT | documentation, https://jsonref.readthedocs.io/en/latest/ |
| jsonschema | 4.26.0 | MIT | Homepage, https://github.com/python-jsonschema/jsonschema |
| jsonschema-path | 0.5.0 | Apache Software License | Repository, https://github.com/p1c2u/jsonschema-path |
| jsonschema-specifications | 2025.9.1 | MIT | Documentation, https://jsonschema-specifications.readthedocs.io/ |
| keyring | 25.7.0 | MIT | Source, https://github.com/jaraco/keyring |
| markdown-it-py | 4.2.0 | MIT License | Documentation, https://markdown-it-py.readthedocs.io |
| mcp | 1.27.1 | MIT License | Homepage, https://modelcontextprotocol.io |
| mdurl | 0.1.2 | MIT License | Homepage, https://github.com/executablebooks/mdurl |
| more-itertools | 11.0.2 | MIT | Documentation, https://more-itertools.readthedocs.io/en/stable/ |
| multidict | 6.7.1 | Apache License 2.0 | https://github.com/aio-libs/multidict |
| multitasking | 0.0.13 | Apache Software License | https://github.com/ranaroussi/multitasking |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | homepage, https://numpy.org |
| openapi-pydantic | 0.5.1 | MIT License | https://github.com/mike-oakley/openapi-pydantic |
| opentelemetry-api | 1.42.1 | Apache-2.0 | Homepage, https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | Documentation, https://packaging.pypa.io/ |
| pandas | 3.0.3 | Apache-2.0 |  |
| pathable | 0.6.0 | Apache Software License | Repository, https://github.com/p1c2u/pathable |
| peewee | 4.0.6 | MIT | Repository, https://github.com/coleifer/peewee |
| platformdirs | 4.9.6 | MIT | Changelog, https://platformdirs.readthedocs.io/en/latest/changelog.html |
| propcache | 0.5.2 | Apache Software License | https://github.com/aio-libs/propcache |
| protobuf | 7.35.0 | BSD-3-Clause | https://developers.google.com/protocol-buffers/ |
| py-key-value-aio | 0.4.4 | Apache Software License |  |
| pycparser | 3.0 | BSD-3-Clause | Homepage, https://github.com/eliben/pycparser |
| pydantic | 2.13.4 | MIT | Homepage, https://github.com/pydantic/pydantic |
| pydantic_core | 2.46.4 | MIT | Funding, https://github.com/sponsors/samuelcolvin |
| pydantic-settings | 2.14.1 | MIT | Homepage, https://github.com/pydantic/pydantic-settings |
| Pygments | 2.20.0 | BSD-2-Clause | Homepage, https://pygments.org |
| PyInstaller-bootloader | embedded | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | https://pyinstaller.org/ |
| PyJWT | 2.12.1 | MIT | Homepage, https://github.com/jpadilla/pyjwt |
| pyperclip | 1.11.0 | BSD License | Homepage, https://github.com/asweigart/pyperclip |
| python-dateutil | 2.9.0.post0 | BSD License | https://github.com/dateutil/dateutil |
| python-dotenv | 1.2.2 | BSD-3-Clause | Source, https://github.com/theskumar/python-dotenv |
| python-multipart | 0.0.27 | Apache-2.0 | Homepage, https://github.com/Kludex/python-multipart |
| pytz | 2026.2 | MIT License | http://pythonhosted.org/pytz |
| PyYAML | 6.0.3 | MIT License | https://pyyaml.org/ |
| referencing | 0.37.0 | MIT | Documentation, https://referencing.readthedocs.io/ |
| requests | 2.34.2 | Apache Software License | Documentation, https://requests.readthedocs.io |
| rich | 15.0.0 | MIT License | Documentation, https://rich.readthedocs.io/en/latest/ |
| rich-rst | 2.0.1 | MIT | Bug Tracker, https://github.com/wasi-master/rich-rst/issues |
| rpds-py | 0.30.0 | MIT | Documentation, https://rpds.readthedocs.io/ |
| ruff | 0.15.14 | MIT | Changelog, https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| soupsieve | 2.8.3 | MIT | Homepage, https://github.com/facelessuser/soupsieve |
| sse-starlette | 3.4.4 | BSD-3-Clause | Homepage, https://github.com/sysid/sse-starlette |
| starlette | 0.52.1 | BSD-3-Clause | Homepage, https://github.com/Kludex/starlette |
| typing_extensions | 4.15.0 | PSF-2.0 | Bug Tracker, https://github.com/python/typing_extensions/issues |
| typing-inspection | 0.4.2 | MIT | Homepage, https://github.com/pydantic/typing-inspection |
| uncalled-for | 0.3.2 | MIT | Repository, https://github.com/chrisguidry/uncalled-for |
| urllib3 | 2.7.0 | MIT | Changelog, https://github.com/urllib3/urllib3/blob/main/CHANGES.rst |
| uuid7 | 0.1.0 | MIT License | https://github.com/stevesimmons/uuid7 |
| uvicorn | 0.40.0 | BSD-3-Clause | Changelog, https://uvicorn.dev/release-notes |
| watchfiles | 1.2.0 | MIT License | Changelog, https://github.com/samuelcolvin/watchfiles/releases |
| webencodings | 0.5.1 | BSD License | https://github.com/SimonSapin/python-webencodings |
| websockets | 16.0 | BSD-3-Clause | Homepage, https://github.com/python-websockets/websockets |
| yarl | 1.24.2 | Apache-2.0 | https://github.com/aio-libs/yarl |
| yfinance | 1.3.0 | Apache Software License | https://github.com/ranaroussi/yfinance |
| zipp | 4.1.0 | MIT | Source, https://github.com/jaraco/zipp |

### Python — vysted-sec-edgar-mcp-sidecar

| Name | Version | Licence | URL |
|---|---|---|---|
| aiofiles | 25.1.0 | Apache Software License | Changelog, https://github.com/Tinche/aiofiles#history |
| annotated-doc | 0.0.4 | MIT | Homepage, https://github.com/fastapi/annotated-doc |
| annotated-types | 0.7.0 | MIT License | Homepage, https://github.com/annotated-types/annotated-types |
| anyio | 4.13.0 | MIT | Documentation, https://anyio.readthedocs.io/en/latest/ |
| attrs | 26.1.0 | MIT | Documentation, https://www.attrs.org/ |
| beautifulsoup4 | 4.14.3 | MIT License | Download, https://www.crummy.com/software/BeautifulSoup/bs4/download/ |
| cffi | 2.0.0 | MIT | Documentation, https://cffi.readthedocs.io/ |
| charset-normalizer | 3.4.7 | MIT | Changelog, https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md |
| click | 8.4.0 | BSD-3-Clause | Changes, https://click.palletsprojects.com/page/changes/ |
| cryptography | 48.0.0 | Apache-2.0 OR BSD-3-Clause | changelog, https://cryptography.io/en/latest/changelog/ |
| edgartools | 5.31.3 | MIT | Homepage, https://github.com/dgunning/edgartools |
| filelock | 3.29.0 | MIT | Documentation, https://py-filelock.readthedocs.io |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| httpcore | 1.0.9 | BSD-3-Clause | Documentation, https://www.encode.io/httpcore |
| httpx | 0.28.1 | BSD License | Changelog, https://github.com/encode/httpx/blob/master/CHANGELOG.md |
| httpx-sse | 0.4.3 | MIT | Homepage, https://github.com/florimondmanca/httpx-sse |
| httpxthrottlecache | 0.3.5 | MIT | Homepage, https://github.com/paultiq/httpxthrottlecache |
| humanize | 4.15.0 | MIT | Documentation, https://humanize.readthedocs.io/ |
| idna | 3.15 | BSD-3-Clause | Changelog, https://github.com/kjd/idna/blob/master/HISTORY.md |
| Jinja2 | 3.1.6 | BSD License | Changes, https://jinja.palletsprojects.com/changes/ |
| jsonschema | 4.26.0 | MIT | Homepage, https://github.com/python-jsonschema/jsonschema |
| jsonschema-specifications | 2025.9.1 | MIT | Documentation, https://jsonschema-specifications.readthedocs.io/ |
| lxml | 6.1.1 | BSD-3-Clause | https://lxml.de/ |
| markdown-it-py | 4.2.0 | MIT License | Documentation, https://markdown-it-py.readthedocs.io |
| MarkupSafe | 3.0.3 | BSD-3-Clause | Donate, https://palletsprojects.com/donate |
| mcp | 1.27.1 | MIT License | Homepage, https://modelcontextprotocol.io |
| mdurl | 0.1.2 | MIT License | Homepage, https://github.com/executablebooks/mdurl |
| nest-asyncio | 1.6.0 | BSD License | https://github.com/erdewit/nest_asyncio |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | homepage, https://numpy.org |
| orjson | 3.11.9 | MPL-2.0 AND (Apache-2.0 OR MIT) | changelog, https://github.com/ijl/orjson/blob/master/CHANGELOG.md |
| pandas | 3.0.3 | Apache-2.0 |  |
| pyarrow | 24.0.0 | Apache-2.0 | Homepage, https://arrow.apache.org/ |
| pycparser | 3.0 | BSD-3-Clause | Homepage, https://github.com/eliben/pycparser |
| pydantic | 2.13.4 | MIT | Homepage, https://github.com/pydantic/pydantic |
| pydantic_core | 2.46.4 | MIT | Funding, https://github.com/sponsors/samuelcolvin |
| pydantic-settings | 2.14.1 | MIT | Homepage, https://github.com/pydantic/pydantic-settings |
| Pygments | 2.20.0 | BSD-2-Clause | Homepage, https://pygments.org |
| PyInstaller-bootloader | embedded | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | https://pyinstaller.org/ |
| PyJWT | 2.12.1 | MIT | Homepage, https://github.com/jpadilla/pyjwt |
| pyrate-limiter | 4.1.0 | MIT | Homepage, https://github.com/vutran1710/PyrateLimiter |
| python-dateutil | 2.9.0.post0 | BSD License | https://github.com/dateutil/dateutil |
| python-dotenv | 1.2.2 | BSD-3-Clause | Source, https://github.com/theskumar/python-dotenv |
| python-multipart | 0.0.29 | Apache-2.0 | Homepage, https://github.com/Kludex/python-multipart |
| rank-bm25 | 0.2.2 | Apache-2.0 | https://github.com/dorianbrown/rank_bm25 |
| RapidFuzz | 3.14.5 | MIT | Homepage, https://github.com/rapidfuzz/RapidFuzz |
| referencing | 0.37.0 | MIT | Documentation, https://referencing.readthedocs.io/ |
| requests | 2.34.2 | Apache Software License | Documentation, https://requests.readthedocs.io |
| rich | 15.0.0 | MIT License | Documentation, https://rich.readthedocs.io/en/latest/ |
| rpds-py | 0.30.0 | MIT | Documentation, https://rpds.readthedocs.io/ |
| shellingham | 1.5.4 | ISC License (ISCL) | https://github.com/sarugaku/shellingham |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| soupsieve | 2.8.3 | MIT | Homepage, https://github.com/facelessuser/soupsieve |
| sse-starlette | 3.4.4 | BSD-3-Clause | Homepage, https://github.com/sysid/sse-starlette |
| stamina | 26.1.0 | MIT | Documentation, https://stamina.hynek.me/ |
| starlette | 1.0.0 | BSD-3-Clause | Homepage, https://github.com/Kludex/starlette |
| tabulate | 0.10.0 | MIT | Homepage, https://github.com/astanin/python-tabulate |
| tenacity | 9.1.4 | Apache Software License | https://github.com/jd/tenacity |
| textdistance | 4.6.3 | MIT License | https://github.com/orsinium/textdistance |
| truststore | 0.10.4 | MIT | Documentation, https://truststore.readthedocs.io |
| typer | 0.25.1 | MIT | Homepage, https://github.com/fastapi/typer |
| typing_extensions | 4.15.0 | PSF-2.0 | Bug Tracker, https://github.com/python/typing_extensions/issues |
| typing-inspection | 0.4.2 | MIT | Homepage, https://github.com/pydantic/typing-inspection |
| urllib3 | 2.7.0 | MIT | Changelog, https://github.com/urllib3/urllib3/blob/main/CHANGES.rst |
| uvicorn | 0.47.0 | BSD-3-Clause | Changelog, https://uvicorn.dev/release-notes |

### npm (frontend, runtime/prod only)

| Name | Version | Licence | URL |
|---|---|---|---|
| @babel/runtime | 7.29.2 | MIT | https://babel.dev/docs/en/next/babel-runtime |
| @floating-ui/core | 1.7.5 | MIT | https://floating-ui.com |
| @floating-ui/dom | 1.7.6 | MIT | https://floating-ui.com |
| @floating-ui/react-dom | 2.1.8 | MIT | https://floating-ui.com/docs/react-dom |
| @floating-ui/utils | 0.2.11 | MIT | https://floating-ui.com |
| @radix-ui/number | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/primitive | 1.1.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-accessible-icon | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-accordion | 1.2.12 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-alert-dialog | 1.1.15 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-arrow | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-aspect-ratio | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-avatar | 1.1.10 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-checkbox | 1.3.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-collapsible | 1.1.12 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-collection | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-compose-refs | 1.1.2 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-context | 1.1.2 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-context-menu | 2.2.16 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-dialog | 1.1.15 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-direction | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-dismissable-layer | 1.1.11 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-dropdown-menu | 2.1.16 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-focus-guards | 1.1.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-focus-scope | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-form | 0.1.8 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-hover-card | 1.1.15 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-id | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-label | 2.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-menu | 2.1.16 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-menubar | 1.1.16 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-navigation-menu | 1.2.14 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-one-time-password-field | 0.1.8 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-password-toggle-field | 0.1.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-popover | 1.1.15 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-popper | 1.2.8 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-portal | 1.1.9 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-presence | 1.1.5 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-primitive | 2.1.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-progress | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-radio-group | 1.3.8 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-roving-focus | 1.1.11 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-scroll-area | 1.2.10 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-select | 2.2.6 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-separator | 1.1.7 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-slider | 1.3.6 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-slot | 1.2.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-switch | 1.2.6 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-tabs | 1.1.13 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-toast | 1.2.15 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-toggle | 1.1.10 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-toggle-group | 1.1.11 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-toolbar | 1.1.11 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-tooltip | 1.2.8 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-callback-ref | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-controllable-state | 1.2.2 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-effect-event | 0.0.2 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-escape-keydown | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-is-hydrated | 0.1.0 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-layout-effect | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-previous | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-rect | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-use-size | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @radix-ui/react-visually-hidden | 1.2.3 | MIT | https://radix-ui.com/primitives |
| @radix-ui/rect | 1.1.1 | MIT | https://radix-ui.com/primitives |
| @tauri-apps/api | 2.11.0 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri#readme |
| @tauri-apps/plugin-notification | 2.3.3 | MIT OR Apache-2.0 | https://github.com/tauri-apps/plugins-workspace#readme |
| @tauri-apps/plugin-shell | 2.3.5 | MIT OR Apache-2.0 | https://github.com/tauri-apps/plugins-workspace#readme |
| @tauri-apps/plugin-updater | 2.10.1 | MIT OR Apache-2.0 | https://github.com/tauri-apps/plugins-workspace#readme |
| @tiptap/core | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-blockquote | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-bold | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-bubble-menu | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-bullet-list | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-code | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-code-block | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-document | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-dropcursor | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-floating-menu | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-gapcursor | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-hard-break | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-heading | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-horizontal-rule | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-italic | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-link | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-list | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-list-item | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-list-keymap | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-ordered-list | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-paragraph | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-strike | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-table | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-table-cell | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-table-header | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-table-row | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-text | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extension-underline | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/extensions | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/markdown | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/pm | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/react | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/starter-kit | 3.25.0 | MIT | https://tiptap.dev |
| @tiptap/suggestion | 3.25.0 | MIT | https://tiptap.dev |
| @types/d3-color | 3.1.3 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-color |
| @types/d3-drag | 3.0.7 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-drag |
| @types/d3-interpolate | 3.0.4 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-interpolate |
| @types/d3-selection | 3.0.11 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-selection |
| @types/d3-transition | 3.0.9 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-transition |
| @types/d3-zoom | 3.0.8 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/d3-zoom |
| @types/pako | 2.0.4 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/pako |
| @types/raf | 3.4.3 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/raf |
| @types/react | 19.2.14 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react |
| @types/react-dom | 19.2.3 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react-dom |
| @types/trusted-types | 2.0.7 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/trusted-types |
| @types/use-sync-external-store | 0.0.6 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/use-sync-external-store |
| @xyflow/react | 12.10.2 | MIT | https://reactflow.dev |
| @xyflow/system | 0.0.76 | MIT | https://github.com/xyflow/xyflow#readme |
| aria-hidden | 1.2.6 | MIT | https://github.com/theKashey/aria-hidden#readme |
| base64-arraybuffer | 1.0.2 | MIT | https://github.com/niklasvh/base64-arraybuffer |
| canvg | 3.0.11 | MIT | https://github.com/canvg/canvg#readme |
| class-variance-authority | 0.7.1 | Apache-2.0 | https://github.com/joe-bell/cva#readme |
| classcat | 5.0.5 | MIT | https://github.com/jorgebucaran/classcat#readme |
| clsx | 2.1.1 | MIT | https://github.com/lukeed/clsx#readme |
| cmdk | 1.1.1 | MIT | https://github.com/pacocoursey/cmdk#readme |
| complex.js | 2.4.3 | MIT | https://raw.org/article/complex-numbers-in-javascript/ |
| core-js | 3.49.0 | MIT | https://core-js.io |
| css-line-break | 2.1.0 | MIT | https://github.com/niklasvh/css-line-break#readme |
| csstype | 3.2.3 | MIT | https://github.com/frenic/csstype#readme |
| d3-color | 3.1.0 | ISC | https://d3js.org/d3-color/ |
| d3-dispatch | 3.0.1 | ISC | https://d3js.org/d3-dispatch/ |
| d3-drag | 3.0.0 | ISC | https://d3js.org/d3-drag/ |
| d3-ease | 3.0.1 | BSD-3-Clause | https://d3js.org/d3-ease/ |
| d3-interpolate | 3.0.1 | ISC | https://d3js.org/d3-interpolate/ |
| d3-selection | 3.0.0 | ISC | https://d3js.org/d3-selection/ |
| d3-timer | 3.0.1 | ISC | https://d3js.org/d3-timer/ |
| d3-transition | 3.0.1 | ISC | https://d3js.org/d3-transition/ |
| d3-zoom | 3.0.0 | ISC | https://d3js.org/d3-zoom/ |
| decimal.js | 10.6.0 | MIT | https://github.com/MikeMcl/decimal.js#readme |
| detect-node-es | 1.1.0 | MIT | https://github.com/thekashey/detect-node |
| dockview | 6.2.2 | MIT | https://github.com/mathuo/dockview |
| dockview-core | 6.2.2 | MIT | https://github.com/mathuo/dockview |
| dompurify | 3.4.8 | (MPL-2.0 OR Apache-2.0) | https://github.com/cure53/DOMPurify |
| escape-latex | 1.2.0 | MIT | https://github.com/dangmai/escape-latex#readme |
| fancy-canvas | 2.1.0 | MIT |  |
| fast-equals | 5.4.0 | MIT | https://github.com/planttheidea/fast-equals#readme |
| fast-png | 6.4.0 | MIT | https://github.com/image-js/fast-png#readme |
| fflate | 0.8.3 | MIT | https://101arrowz.github.io/fflate |
| fraction.js | 5.3.4 | MIT | https://raw.org/article/rational-numbers-in-javascript/ |
| framer-motion | 12.38.0 | MIT | https://github.com/motiondivision/motion#readme |
| get-nonce | 1.0.1 | MIT | https://github.com/theKashey/get-nonce |
| html-to-image | 1.11.13 | MIT | https://github.com/bubkoo/html-to-image#readme |
| html2canvas | 1.4.1 | MIT | https://html2canvas.hertzen.com |
| iobuffer | 5.4.0 | MIT | https://github.com/image-js/iobuffer#readme |
| javascript-natural-sort | 0.7.1 | MIT | https://github.com/Bill4Time/javascript-natural-sort |
| jspdf | 4.2.1 | MIT | https://github.com/parallax/jsPDF |
| jspdf-autotable | 5.0.8 | MIT | https://simonbengtsson.github.io/jsPDF-AutoTable |
| lightweight-charts | 5.2.0 | Apache-2.0 | https://www.tradingview.com/lightweight-charts/ |
| linkifyjs | 4.3.3 | MIT | https://linkify.js.org |
| lucide-react | 1.14.0 | ISC | https://lucide.dev |
| marked | 17.0.6 | MIT | https://marked.js.org |
| mathjs | 15.2.0 | Apache-2.0 | https://mathjs.org |
| motion-dom | 12.38.0 | MIT | https://github.com/motiondivision/motion#readme |
| motion-utils | 12.36.0 | MIT | https://github.com/motiondivision/motion#readme |
| orderedmap | 2.1.1 | MIT | https://github.com/marijnh/orderedmap#readme |
| pako | 2.1.0 | (MIT AND Zlib) | https://github.com/nodeca/pako#readme |
| performance-now | 2.1.0 | MIT | https://github.com/braveg1rl/performance-now |
| prosemirror-changeset | 2.4.1 | MIT |  |
| prosemirror-commands | 1.7.1 | MIT | https://github.com/prosemirror/prosemirror-commands#readme |
| prosemirror-dropcursor | 1.8.2 | MIT | https://github.com/prosemirror/prosemirror-dropcursor#readme |
| prosemirror-gapcursor | 1.4.1 | MIT | https://github.com/prosemirror/prosemirror-gapcursor#readme |
| prosemirror-history | 1.5.0 | MIT | https://github.com/prosemirror/prosemirror-history#readme |
| prosemirror-inputrules | 1.5.1 | MIT | https://github.com/prosemirror/prosemirror-inputrules#readme |
| prosemirror-keymap | 1.2.3 | MIT | https://github.com/prosemirror/prosemirror-keymap#readme |
| prosemirror-model | 1.25.7 | MIT |  |
| prosemirror-schema-list | 1.5.1 | MIT | https://github.com/prosemirror/prosemirror-schema-list#readme |
| prosemirror-state | 1.4.4 | MIT | https://github.com/prosemirror/prosemirror-state#readme |
| prosemirror-tables | 1.8.5 | MIT | https://github.com/ProseMirror/prosemirror-tables#readme |
| prosemirror-transform | 1.12.0 | MIT | https://github.com/prosemirror/prosemirror-transform#readme |
| prosemirror-view | 1.41.8 | MIT |  |
| radix-ui | 1.4.3 | MIT | https://radix-ui.com/primitives |
| raf | 3.4.1 | MIT | https://github.com/chrisdickinson/raf#readme |
| react | 19.2.6 | MIT | https://react.dev/ |
| react-dom | 19.2.6 | MIT | https://react.dev/ |
| react-remove-scroll | 2.7.2 | MIT | https://github.com/theKashey/react-remove-scroll#readme |
| react-remove-scroll-bar | 2.3.8 | MIT | https://github.com/theKashey/react-remove-scroll-bar#readme |
| react-style-singleton | 2.2.3 | MIT | https://github.com/theKashey/react-style-singleton#readme |
| regenerator-runtime | 0.13.11 | MIT | https://github.com/facebook/regenerator/tree/main#readme |
| rgbcolor | 1.0.1 | MIT | https://github.com/yetzt/node-rgbcolor#readme |
| rope-sequence | 1.3.4 | MIT | https://github.com/marijnh/rope-sequence#readme |
| scheduler | 0.27.0 | MIT | https://react.dev/ |
| seedrandom | 3.0.5 | MIT | http://davidbau.com/archives/2010/01/30/random_seeds_coded_hints_and_quintillions.html |
| stackblur-canvas | 2.7.0 | MIT | http://www.quasimondo.com/StackBlurForCanvas/StackBlurDemo.html |
| svg-pathdata | 6.0.3 | MIT | https://github.com/nfroidure/svg-pathdata#readme |
| tailwind-merge | 3.6.0 | MIT | https://github.com/dcastil/tailwind-merge |
| text-segmentation | 1.0.3 | MIT | https://github.com/niklasvh/text-segmentation |
| tiny-emitter | 2.1.0 | MIT | https://github.com/scottcorgan/tiny-emitter#readme |
| tslib | 2.8.1 | 0BSD | https://www.typescriptlang.org/ |
| typed-function | 4.2.2 | MIT | https://github.com/josdejong/typed-function |
| use-callback-ref | 1.3.3 | MIT | https://github.com/theKashey/use-callback-ref#readme |
| use-sidecar | 1.1.3 | MIT | https://github.com/theKashey/use-sidecar |
| use-sync-external-store | 1.6.0 | MIT | https://github.com/facebook/react#readme |
| utrie | 1.0.2 | MIT | https://github.com/niklasvh/utrie |
| w3c-keyname | 2.2.8 | MIT | https://github.com/marijnh/w3c-keyname#readme |
| zustand | 4.5.7 | MIT | https://github.com/pmndrs/zustand |
| zustand | 5.0.13 | MIT | https://github.com/pmndrs/zustand |

### Rust crates (src-tauri, normal deps only)

| Name | Version | Licence | URL |
|---|---|---|---|
| adler2 | 2.0.1 | 0BSD OR MIT OR Apache-2.0 | https://github.com/oyvindln/adler2 |
| aes | 0.8.4 | MIT OR Apache-2.0 | https://github.com/RustCrypto/block-ciphers |
| aho-corasick | 1.1.4 | Unlicense OR MIT | https://github.com/BurntSushi/aho-corasick |
| alloc-no-stdlib | 2.0.4 | BSD-3-Clause | https://github.com/dropbox/rust-alloc-no-stdlib |
| alloc-stdlib | 0.2.2 | BSD-3-Clause | https://github.com/dropbox/rust-alloc-no-stdlib |
| android_system_properties | 0.1.5 | MIT/Apache-2.0 | https://github.com/nical/android_system_properties |
| anyhow | 1.0.102 | MIT OR Apache-2.0 | https://github.com/dtolnay/anyhow |
| arbitrary | 1.4.2 | MIT OR Apache-2.0 | https://github.com/rust-fuzz/arbitrary/ |
| async-broadcast | 0.7.2 | MIT OR Apache-2.0 | https://github.com/smol-rs/async-broadcast |
| async-channel | 2.5.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-channel |
| async-executor | 1.14.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-executor |
| async-io | 2.6.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-io |
| async-lock | 3.4.2 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-lock |
| async-process | 2.5.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-process |
| async-recursion | 1.1.1 | MIT OR Apache-2.0 | https://github.com/dcchut/async-recursion |
| async-signal | 0.2.14 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-signal |
| async-task | 4.7.1 | Apache-2.0 OR MIT | https://github.com/smol-rs/async-task |
| async-trait | 0.1.89 | MIT OR Apache-2.0 | https://github.com/dtolnay/async-trait |
| atk | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| atk-sys | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| atomic-waker | 1.1.2 | Apache-2.0 OR MIT | https://github.com/smol-rs/atomic-waker |
| base64 | 0.21.7 | MIT OR Apache-2.0 | https://github.com/marshallpierce/rust-base64 |
| base64 | 0.22.1 | MIT OR Apache-2.0 | https://github.com/marshallpierce/rust-base64 |
| bit-set | 0.8.0 | Apache-2.0 OR MIT | https://github.com/contain-rs/bit-set |
| bit-vec | 0.8.0 | Apache-2.0 OR MIT | https://github.com/contain-rs/bit-vec |
| bitflags | 1.3.2 | MIT/Apache-2.0 | https://github.com/bitflags/bitflags |
| bitflags | 2.11.1 | MIT OR Apache-2.0 | https://github.com/bitflags/bitflags |
| block-buffer | 0.10.4 | MIT OR Apache-2.0 | https://github.com/RustCrypto/utils |
| block-padding | 0.3.3 | MIT OR Apache-2.0 | https://github.com/RustCrypto/utils |
| block2 | 0.6.2 | MIT | https://github.com/madsmtm/objc2 |
| blocking | 1.6.2 | Apache-2.0 OR MIT | https://github.com/smol-rs/blocking |
| brotli | 8.0.2 | BSD-3-Clause AND MIT | https://github.com/dropbox/rust-brotli |
| brotli-decompressor | 5.0.0 | BSD-3-Clause/MIT | https://github.com/dropbox/rust-brotli-decompressor |
| bs58 | 0.5.1 | MIT/Apache-2.0 | https://github.com/Nullus157/bs58-rs |
| bumpalo | 3.20.2 | MIT OR Apache-2.0 | https://github.com/fitzgen/bumpalo |
| bytemuck | 1.25.0 | Zlib OR Apache-2.0 OR MIT | https://github.com/Lokathor/bytemuck |
| byteorder | 1.5.0 | Unlicense OR MIT | https://github.com/BurntSushi/byteorder |
| bytes | 1.11.1 | MIT | https://github.com/tokio-rs/bytes |
| cairo-rs | 0.18.5 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| cairo-sys-rs | 0.18.2 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| camino | 1.2.2 | MIT OR Apache-2.0 | https://github.com/camino-rs/camino |
| cargo_metadata | 0.19.2 | MIT | https://github.com/oli-obk/cargo_metadata |
| cargo-platform | 0.1.9 | MIT OR Apache-2.0 | https://github.com/rust-lang/cargo |
| cbc | 0.1.2 | MIT OR Apache-2.0 | https://github.com/RustCrypto/block-modes |
| cesu8 | 1.1.0 | Apache-2.0/MIT | https://github.com/emk/cesu8-rs |
| cfb | 0.7.3 | MIT | https://github.com/mdsteele/rust-cfb |
| cfg-if | 1.0.4 | MIT OR Apache-2.0 | https://github.com/rust-lang/cfg-if |
| chrono | 0.4.44 | MIT OR Apache-2.0 | https://github.com/chronotope/chrono |
| cipher | 0.4.4 | MIT OR Apache-2.0 | https://github.com/RustCrypto/traits |
| combine | 4.6.7 | MIT | https://github.com/Marwes/combine |
| concurrent-queue | 2.5.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/concurrent-queue |
| cookie | 0.18.1 | MIT OR Apache-2.0 | https://github.com/SergioBenitez/cookie-rs |
| core-foundation | 0.10.1 | MIT OR Apache-2.0 | https://github.com/servo/core-foundation-rs |
| core-foundation | 0.9.4 | MIT OR Apache-2.0 | https://github.com/servo/core-foundation-rs |
| core-foundation-sys | 0.8.7 | MIT OR Apache-2.0 | https://github.com/servo/core-foundation-rs |
| core-graphics | 0.25.0 | MIT OR Apache-2.0 | https://github.com/servo/core-foundation-rs |
| core-graphics-types | 0.2.0 | MIT OR Apache-2.0 | https://github.com/servo/core-foundation-rs |
| cpufeatures | 0.2.17 | MIT OR Apache-2.0 | https://github.com/RustCrypto/utils |
| crc32fast | 1.5.0 | MIT OR Apache-2.0 | https://github.com/srijs/rust-crc32fast |
| crossbeam-channel | 0.5.15 | MIT OR Apache-2.0 | https://github.com/crossbeam-rs/crossbeam |
| crossbeam-utils | 0.8.21 | MIT OR Apache-2.0 | https://github.com/crossbeam-rs/crossbeam |
| crypto-common | 0.1.7 | MIT OR Apache-2.0 | https://github.com/RustCrypto/traits |
| ctor | 0.8.0 | Apache-2.0 OR MIT | https://github.com/mmastrac/rust-ctor |
| ctor-proc-macro | 0.0.7 | Apache-2.0 OR MIT | https://github.com/mmastrac/rust-ctor |
| darling | 0.23.0 | MIT | https://github.com/TedDriggs/darling |
| darling_core | 0.23.0 | MIT | https://github.com/TedDriggs/darling |
| darling_macro | 0.23.0 | MIT | https://github.com/TedDriggs/darling |
| dbus | 0.9.11 | Apache-2.0/MIT | https://github.com/diwic/dbus-rs |
| dbus-secret-service | 4.1.0 | MIT OR Apache-2.0 | https://github.com/brotskydotcom/dbus-secret-service.git |
| deranged | 0.5.8 | MIT OR Apache-2.0 | https://github.com/jhpratt/deranged |
| derive_arbitrary | 1.4.2 | MIT OR Apache-2.0 | https://github.com/rust-fuzz/arbitrary |
| derive_more | 2.1.1 | MIT | https://github.com/JelteF/derive_more |
| derive_more-impl | 2.1.1 | MIT | https://github.com/JelteF/derive_more |
| digest | 0.10.7 | MIT OR Apache-2.0 | https://github.com/RustCrypto/traits |
| dirs | 6.0.0 | MIT OR Apache-2.0 | https://github.com/soc/dirs-rs |
| dirs-sys | 0.5.0 | MIT OR Apache-2.0 | https://github.com/dirs-dev/dirs-sys-rs |
| dispatch2 | 0.3.1 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| displaydoc | 0.2.5 | MIT OR Apache-2.0 | https://github.com/yaahc/displaydoc |
| dlopen2 | 0.8.2 | MIT | https://github.com/OpenByteDev/dlopen2 |
| dlopen2_derive | 0.4.3 | MIT | https://github.com/OpenByteDev/dlopen2 |
| dom_query | 0.27.0 | MIT | https://github.com/niklak/dom_query |
| dpi | 0.1.2 | Apache-2.0 AND MIT | https://github.com/rust-windowing/winit |
| dtoa | 1.0.11 | MIT OR Apache-2.0 | https://github.com/dtolnay/dtoa |
| dtor | 0.3.0 | Apache-2.0 OR MIT | https://github.com/mmastrac/rust-ctor |
| dtor-proc-macro | 0.0.6 | Apache-2.0 OR MIT | https://github.com/mmastrac/rust-ctor |
| dunce | 1.0.5 | CC0-1.0 OR MIT-0 OR Apache-2.0 | https://gitlab.com/kornelski/dunce |
| dyn-clone | 1.0.20 | MIT OR Apache-2.0 | https://github.com/dtolnay/dyn-clone |
| embed_plist | 1.2.2 | MIT OR Apache-2.0 | https://github.com/nvzqz/embed-plist-rs |
| encoding_rs | 0.8.35 | (Apache-2.0 OR MIT) AND BSD-3-Clause | https://github.com/hsivonen/encoding_rs |
| endi | 1.1.1 | MIT | https://github.com/zeenix/endi |
| enumflags2 | 0.7.12 | MIT OR Apache-2.0 | https://github.com/meithecatte/enumflags2 |
| enumflags2_derive | 0.7.12 | MIT OR Apache-2.0 | https://github.com/meithecatte/enumflags2 |
| equivalent | 1.0.2 | Apache-2.0 OR MIT | https://github.com/indexmap-rs/equivalent |
| erased-serde | 0.4.10 | MIT OR Apache-2.0 | https://github.com/dtolnay/erased-serde |
| errno | 0.3.14 | MIT OR Apache-2.0 | https://github.com/lambda-fairy/rust-errno |
| event-listener | 5.4.1 | Apache-2.0 OR MIT | https://github.com/smol-rs/event-listener |
| event-listener-strategy | 0.5.4 | Apache-2.0 OR MIT | https://github.com/smol-rs/event-listener-strategy |
| fastrand | 2.4.1 | Apache-2.0 OR MIT | https://github.com/smol-rs/fastrand |
| fdeflate | 0.3.7 | MIT OR Apache-2.0 | https://github.com/image-rs/fdeflate |
| field-offset | 0.3.6 | MIT OR Apache-2.0 | https://github.com/Diggsey/rust-field-offset |
| filetime | 0.2.29 | MIT/Apache-2.0 | https://github.com/alexcrichton/filetime |
| flate2 | 1.1.9 | MIT OR Apache-2.0 | https://github.com/rust-lang/flate2-rs |
| fnv | 1.0.7 | Apache-2.0 / MIT | https://github.com/servo/rust-fnv |
| foldhash | 0.1.5 | Zlib | https://github.com/orlp/foldhash |
| foldhash | 0.2.0 | Zlib | https://github.com/orlp/foldhash |
| foreign-types | 0.5.0 | MIT/Apache-2.0 | https://github.com/sfackler/foreign-types |
| foreign-types-macros | 0.2.3 | MIT/Apache-2.0 | https://github.com/sfackler/foreign-types |
| foreign-types-shared | 0.3.1 | MIT/Apache-2.0 | https://github.com/sfackler/foreign-types |
| form_urlencoded | 1.2.2 | MIT OR Apache-2.0 | https://github.com/servo/rust-url |
| futures-channel | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-core | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-executor | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-io | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-lite | 2.6.1 | Apache-2.0 OR MIT | https://github.com/smol-rs/futures-lite |
| futures-macro | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-sink | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-task | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| futures-util | 0.3.32 | MIT OR Apache-2.0 | https://github.com/rust-lang/futures-rs |
| gdk | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gdk-pixbuf | 0.18.5 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| gdk-pixbuf-sys | 0.18.0 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| gdk-sys | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gdkwayland-sys | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gdkx11 | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gdkx11-sys | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| generic-array | 0.14.7 | MIT | https://github.com/fizyk20/generic-array.git |
| getrandom | 0.2.17 | MIT OR Apache-2.0 | https://github.com/rust-random/getrandom |
| getrandom | 0.3.4 | MIT OR Apache-2.0 | https://github.com/rust-random/getrandom |
| getrandom | 0.4.2 | MIT OR Apache-2.0 | https://github.com/rust-random/getrandom |
| gio | 0.18.4 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| gio-sys | 0.18.1 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| glib | 0.18.5 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| glib-macros | 0.18.5 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| glib-sys | 0.18.1 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| glob | 0.3.3 | MIT OR Apache-2.0 | https://github.com/rust-lang/glob |
| gobject-sys | 0.18.0 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| gtk | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gtk-sys | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| gtk3-macros | 0.18.2 | MIT | https://github.com/gtk-rs/gtk3-rs |
| hashbrown | 0.12.3 | MIT OR Apache-2.0 | https://github.com/rust-lang/hashbrown |
| hashbrown | 0.15.5 | MIT OR Apache-2.0 | https://github.com/rust-lang/hashbrown |
| hashbrown | 0.17.1 | MIT OR Apache-2.0 | https://github.com/rust-lang/hashbrown |
| heck | 0.4.1 | MIT OR Apache-2.0 | https://github.com/withoutboats/heck |
| heck | 0.5.0 | MIT OR Apache-2.0 | https://github.com/withoutboats/heck |
| hermit-abi | 0.5.2 | MIT OR Apache-2.0 | https://github.com/hermit-os/hermit-rs |
| hex | 0.4.3 | MIT OR Apache-2.0 | https://github.com/KokaKiwi/rust-hex |
| hkdf | 0.12.4 | MIT OR Apache-2.0 | https://github.com/RustCrypto/KDFs/ |
| hmac | 0.12.1 | MIT OR Apache-2.0 | https://github.com/RustCrypto/MACs |
| html5ever | 0.38.0 | MIT OR Apache-2.0 | https://github.com/servo/html5ever |
| http | 1.4.0 | MIT OR Apache-2.0 | https://github.com/hyperium/http |
| http-body | 1.0.1 | MIT | https://github.com/hyperium/http-body |
| http-body-util | 0.1.3 | MIT | https://github.com/hyperium/http-body |
| httparse | 1.10.1 | MIT OR Apache-2.0 | https://github.com/seanmonstar/httparse |
| hyper | 1.9.0 | MIT | https://github.com/hyperium/hyper |
| hyper-rustls | 0.27.9 | Apache-2.0 OR ISC OR MIT | https://github.com/rustls/hyper-rustls |
| hyper-util | 0.1.20 | MIT | https://github.com/hyperium/hyper-util |
| iana-time-zone | 0.1.65 | MIT OR Apache-2.0 | https://github.com/strawlab/iana-time-zone |
| iana-time-zone-haiku | 0.1.2 | MIT OR Apache-2.0 | https://github.com/strawlab/iana-time-zone |
| ico | 0.5.0 | MIT | https://github.com/mdsteele/rust-ico |
| icu_collections | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_locale_core | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_normalizer | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_normalizer_data | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_properties | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_properties_data | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| icu_provider | 2.2.0 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| id-arena | 2.3.0 | MIT/Apache-2.0 | https://github.com/fitzgen/id-arena |
| ident_case | 1.0.1 | MIT/Apache-2.0 | https://github.com/TedDriggs/ident_case |
| idna | 1.1.0 | MIT OR Apache-2.0 | https://github.com/servo/rust-url/ |
| idna_adapter | 1.2.2 | Apache-2.0 OR MIT | https://github.com/hsivonen/idna_adapter |
| indexmap | 1.9.3 | Apache-2.0 OR MIT | https://github.com/bluss/indexmap |
| indexmap | 2.14.0 | Apache-2.0 OR MIT | https://github.com/indexmap-rs/indexmap |
| infer | 0.19.0 | MIT | https://github.com/bojand/infer |
| inout | 0.1.4 | MIT OR Apache-2.0 | https://github.com/RustCrypto/utils |
| ipnet | 2.12.0 | MIT OR Apache-2.0 | https://github.com/krisprice/ipnet |
| is-docker | 0.2.0 | MIT | https://github.com/TheLarkInn/is-docker |
| is-wsl | 0.4.0 | MIT | https://github.com/TheLarkInn/is-wsl |
| itoa | 1.0.18 | MIT OR Apache-2.0 | https://github.com/dtolnay/itoa |
| javascriptcore-rs | 1.1.2 | MIT | https://github.com/tauri-apps/javascriptcore-rs |
| javascriptcore-rs-sys | 1.1.1 | MIT | https://github.com/tauri-apps/javascriptcore-rs |
| jni | 0.21.1 | MIT/Apache-2.0 | https://github.com/jni-rs/jni-rs |
| jni | 0.22.4 | MIT OR Apache-2.0 | https://github.com/jni-rs/jni-rs |
| jni-macros | 0.22.4 | MIT OR Apache-2.0 | https://github.com/jni-rs/jni-rs |
| jni-sys | 0.3.1 | MIT OR Apache-2.0 | https://github.com/jni-rs/jni-sys |
| jni-sys | 0.4.1 | MIT OR Apache-2.0 | https://github.com/jni-rs/jni-sys |
| jni-sys-macros | 0.4.1 | MIT OR Apache-2.0 | https://github.com/jni-rs/jni-sys |
| js-sys | 0.3.98 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/js-sys |
| json-patch | 3.0.1 | MIT/Apache-2.0 | https://github.com/idubrov/json-patch |
| jsonptr | 0.6.3 | MIT OR Apache-2.0 | https://github.com/chanced/jsonptr |
| keyboard-types | 0.7.0 | MIT OR Apache-2.0 | https://github.com/pyfisch/keyboard-types |
| keyring | 3.6.3 | MIT OR Apache-2.0 | https://github.com/hwchen/keyring-rs.git |
| leb128fmt | 0.1.0 | MIT OR Apache-2.0 | https://github.com/bluk/leb128fmt |
| libappindicator | 0.9.0 | Apache-2.0 OR MIT |  |
| libappindicator-sys | 0.9.0 | Apache-2.0 OR MIT |  |
| libc | 0.2.186 | MIT OR Apache-2.0 | https://github.com/rust-lang/libc |
| libdbus-sys | 0.2.7 | Apache-2.0/MIT | https://github.com/diwic/dbus-rs |
| libloading | 0.7.4 | ISC | https://github.com/nagisa/rust_libloading/ |
| libredox | 0.1.16 | MIT | https://gitlab.redox-os.org/redox-os/libredox.git |
| linux-raw-sys | 0.12.1 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/sunfishcode/linux-raw-sys |
| litemap | 0.8.2 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| lock_api | 0.4.14 | MIT OR Apache-2.0 | https://github.com/Amanieu/parking_lot |
| log | 0.4.29 | MIT OR Apache-2.0 | https://github.com/rust-lang/log |
| mac-notification-sys | 0.6.12 | MIT/Apache-2.0 | https://github.com/h4llow3En/mac-notification-sys |
| markup5ever | 0.38.0 | MIT OR Apache-2.0 | https://github.com/servo/html5ever |
| memchr | 2.8.0 | Unlicense OR MIT | https://github.com/BurntSushi/memchr |
| memoffset | 0.9.1 | MIT | https://github.com/Gilnaa/memoffset |
| mime | 0.3.17 | MIT OR Apache-2.0 | https://github.com/hyperium/mime |
| minisign-verify | 0.2.5 | MIT | https://github.com/jedisct1/rust-minisign-verify |
| miniz_oxide | 0.8.9 | MIT OR Zlib OR Apache-2.0 | https://github.com/Frommi/miniz_oxide/tree/master/miniz_oxide |
| mio | 1.2.0 | MIT | https://github.com/tokio-rs/mio |
| muda | 0.19.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/muda |
| ndk | 0.9.0 | MIT OR Apache-2.0 | https://github.com/rust-mobile/ndk |
| ndk-sys | 0.6.0+11769913 | MIT OR Apache-2.0 | https://github.com/rust-mobile/ndk |
| new_debug_unreachable | 1.0.6 | MIT | https://github.com/mbrubeck/rust-debug-unreachable |
| nix | 0.29.0 | MIT | https://github.com/nix-rust/nix |
| notify-rust | 4.17.0 | MIT/Apache-2.0 | https://github.com/hoodie/notify-rust |
| num | 0.4.3 | MIT OR Apache-2.0 | https://github.com/rust-num/num |
| num-bigint | 0.4.6 | MIT OR Apache-2.0 | https://github.com/rust-num/num-bigint |
| num-complex | 0.4.6 | MIT OR Apache-2.0 | https://github.com/rust-num/num-complex |
| num-conv | 0.2.1 | MIT OR Apache-2.0 | https://github.com/jhpratt/num-conv |
| num_enum | 0.7.6 | BSD-3-Clause OR MIT OR Apache-2.0 | https://github.com/illicitonion/num_enum |
| num_enum_derive | 0.7.6 | BSD-3-Clause OR MIT OR Apache-2.0 | https://github.com/illicitonion/num_enum |
| num-integer | 0.1.46 | MIT OR Apache-2.0 | https://github.com/rust-num/num-integer |
| num-iter | 0.1.45 | MIT OR Apache-2.0 | https://github.com/rust-num/num-iter |
| num-rational | 0.4.2 | MIT OR Apache-2.0 | https://github.com/rust-num/num-rational |
| num-traits | 0.2.19 | MIT OR Apache-2.0 | https://github.com/rust-num/num-traits |
| objc2 | 0.6.4 | MIT | https://github.com/madsmtm/objc2 |
| objc2-app-kit | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-cloud-kit | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-data | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-foundation | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-graphics | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-image | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-location | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-core-text | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-encode | 4.1.0 | MIT | https://github.com/madsmtm/objc2 |
| objc2-exception-helper | 0.1.1 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-foundation | 0.3.2 | MIT | https://github.com/madsmtm/objc2 |
| objc2-io-surface | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-osa-kit | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-quartz-core | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-ui-kit | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-user-notifications | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| objc2-web-kit | 0.3.2 | Zlib OR Apache-2.0 OR MIT | https://github.com/madsmtm/objc2 |
| once_cell | 1.21.4 | MIT OR Apache-2.0 | https://github.com/matklad/once_cell |
| open | 5.3.5 | MIT | https://github.com/Byron/open-rs |
| openssl-probe | 0.2.1 | MIT OR Apache-2.0 | https://github.com/rustls/openssl-probe |
| ordered-stream | 0.2.0 | MIT OR Apache-2.0 | https://github.com/danieldg/ordered-stream |
| os_pipe | 1.2.3 | MIT | https://github.com/oconnor663/os_pipe.rs |
| osakit | 0.3.1 | MIT OR Apache-2.0 | https://github.com/mdevils/rust-osakit |
| pango | 0.18.3 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| pango-sys | 0.18.0 | MIT | https://github.com/gtk-rs/gtk-rs-core |
| parking | 2.2.1 | Apache-2.0 OR MIT | https://github.com/smol-rs/parking |
| parking_lot | 0.12.5 | MIT OR Apache-2.0 | https://github.com/Amanieu/parking_lot |
| parking_lot_core | 0.9.12 | MIT OR Apache-2.0 | https://github.com/Amanieu/parking_lot |
| pathdiff | 0.2.3 | MIT/Apache-2.0 | https://github.com/Manishearth/pathdiff |
| percent-encoding | 2.3.2 | MIT OR Apache-2.0 | https://github.com/servo/rust-url/ |
| phf | 0.13.1 | MIT | https://github.com/rust-phf/rust-phf |
| phf_generator | 0.13.1 | MIT | https://github.com/rust-phf/rust-phf |
| phf_macros | 0.13.1 | MIT | https://github.com/rust-phf/rust-phf |
| phf_shared | 0.13.1 | MIT | https://github.com/rust-phf/rust-phf |
| pin-project-lite | 0.2.17 | Apache-2.0 OR MIT | https://github.com/taiki-e/pin-project-lite |
| piper | 0.2.5 | MIT OR Apache-2.0 | https://github.com/smol-rs/piper |
| plist | 1.9.0 | MIT | https://github.com/ebarnard/rust-plist/ |
| png | 0.17.16 | MIT OR Apache-2.0 | https://github.com/image-rs/image-png |
| png | 0.18.1 | MIT OR Apache-2.0 | https://github.com/image-rs/image-png |
| polling | 3.11.0 | Apache-2.0 OR MIT | https://github.com/smol-rs/polling |
| potential_utf | 0.1.5 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| powerfmt | 0.2.0 | MIT OR Apache-2.0 | https://github.com/jhpratt/powerfmt |
| ppv-lite86 | 0.2.21 | MIT OR Apache-2.0 | https://github.com/cryptocorrosion/cryptocorrosion |
| precomputed-hash | 0.1.1 | MIT | https://github.com/emilio/precomputed-hash |
| prettyplease | 0.2.37 | MIT OR Apache-2.0 | https://github.com/dtolnay/prettyplease |
| proc-macro-crate | 1.3.1 | MIT OR Apache-2.0 | https://github.com/bkchr/proc-macro-crate |
| proc-macro-crate | 2.0.2 | MIT OR Apache-2.0 | https://github.com/bkchr/proc-macro-crate |
| proc-macro-crate | 3.5.0 | MIT OR Apache-2.0 | https://github.com/bkchr/proc-macro-crate |
| proc-macro-error | 1.0.4 | MIT OR Apache-2.0 | https://gitlab.com/CreepySkeleton/proc-macro-error |
| proc-macro-error-attr | 1.0.4 | MIT OR Apache-2.0 | https://gitlab.com/CreepySkeleton/proc-macro-error |
| proc-macro2 | 1.0.106 | MIT OR Apache-2.0 | https://github.com/dtolnay/proc-macro2 |
| quick-xml | 0.37.5 | MIT | https://github.com/tafia/quick-xml |
| quick-xml | 0.39.4 | MIT | https://github.com/tafia/quick-xml |
| quote | 1.0.45 | MIT OR Apache-2.0 | https://github.com/dtolnay/quote |
| r-efi | 5.3.0 | MIT OR Apache-2.0 OR LGPL-2.1-or-later | https://github.com/r-efi/r-efi |
| r-efi | 6.0.0 | MIT OR Apache-2.0 OR LGPL-2.1-or-later | https://github.com/r-efi/r-efi |
| rand | 0.8.5 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| rand | 0.9.4 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| rand_chacha | 0.3.1 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| rand_chacha | 0.9.0 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| rand_core | 0.6.4 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| rand_core | 0.9.5 | MIT OR Apache-2.0 | https://github.com/rust-random/rand |
| raw-window-handle | 0.6.2 | MIT OR Apache-2.0 OR Zlib | https://github.com/rust-windowing/raw-window-handle |
| redox_syscall | 0.5.18 | MIT | https://gitlab.redox-os.org/redox-os/syscall |
| redox_users | 0.5.2 | MIT | https://gitlab.redox-os.org/redox-os/users |
| ref-cast | 1.0.25 | MIT OR Apache-2.0 | https://github.com/dtolnay/ref-cast |
| ref-cast-impl | 1.0.25 | MIT OR Apache-2.0 | https://github.com/dtolnay/ref-cast |
| regex | 1.12.3 | MIT OR Apache-2.0 | https://github.com/rust-lang/regex |
| regex-automata | 0.4.14 | MIT OR Apache-2.0 | https://github.com/rust-lang/regex |
| regex-syntax | 0.8.10 | MIT OR Apache-2.0 | https://github.com/rust-lang/regex |
| reqwest | 0.13.3 | MIT OR Apache-2.0 | https://github.com/seanmonstar/reqwest |
| ring | 0.17.14 | Apache-2.0 AND ISC | https://github.com/briansmith/ring |
| rustc-hash | 2.1.2 | Apache-2.0 OR MIT | https://github.com/rust-lang/rustc-hash |
| rustix | 1.1.4 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/rustix |
| rustls | 0.23.40 | Apache-2.0 OR ISC OR MIT | https://github.com/rustls/rustls |
| rustls-native-certs | 0.8.3 | Apache-2.0 OR ISC OR MIT | https://github.com/rustls/rustls-native-certs |
| rustls-pki-types | 1.14.1 | MIT OR Apache-2.0 | https://github.com/rustls/pki-types |
| rustls-platform-verifier | 0.7.0 | MIT OR Apache-2.0 | https://github.com/rustls/rustls-platform-verifier |
| rustls-platform-verifier-android | 0.1.1 | MIT OR Apache-2.0 | https://github.com/rustls/rustls-platform-verifier |
| rustls-webpki | 0.103.13 | ISC | https://github.com/rustls/webpki |
| rustversion | 1.0.22 | MIT OR Apache-2.0 | https://github.com/dtolnay/rustversion |
| same-file | 1.0.6 | Unlicense/MIT | https://github.com/BurntSushi/same-file |
| schannel | 0.1.29 | MIT | https://github.com/steffengy/schannel-rs |
| schemars | 0.8.22 | MIT | https://github.com/GREsau/schemars |
| schemars | 0.9.0 | MIT | https://github.com/GREsau/schemars |
| schemars | 1.2.1 | MIT | https://github.com/GREsau/schemars |
| schemars_derive | 0.8.22 | MIT | https://github.com/GREsau/schemars |
| scopeguard | 1.2.0 | MIT OR Apache-2.0 | https://github.com/bluss/scopeguard |
| secret-service | 4.0.0 | MIT OR Apache-2.0 | https://github.com/hwchen/secret-service-rs.git |
| security-framework | 2.11.1 | MIT OR Apache-2.0 | https://github.com/kornelski/rust-security-framework |
| security-framework | 3.7.0 | MIT OR Apache-2.0 | https://github.com/kornelski/rust-security-framework |
| security-framework-sys | 2.17.0 | MIT OR Apache-2.0 | https://github.com/kornelski/rust-security-framework |
| semver | 1.0.28 | MIT OR Apache-2.0 | https://github.com/dtolnay/semver |
| serde | 1.0.228 | MIT OR Apache-2.0 | https://github.com/serde-rs/serde |
| serde_core | 1.0.228 | MIT OR Apache-2.0 | https://github.com/serde-rs/serde |
| serde_derive | 1.0.228 | MIT OR Apache-2.0 | https://github.com/serde-rs/serde |
| serde_derive_internals | 0.29.1 | MIT OR Apache-2.0 | https://github.com/serde-rs/serde |
| serde_json | 1.0.149 | MIT OR Apache-2.0 | https://github.com/serde-rs/json |
| serde_repr | 0.1.20 | MIT OR Apache-2.0 | https://github.com/dtolnay/serde-repr |
| serde_spanned | 0.6.9 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| serde_spanned | 1.1.1 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| serde-untagged | 0.1.9 | MIT OR Apache-2.0 | https://github.com/dtolnay/serde-untagged |
| serde_with | 3.20.0 | MIT OR Apache-2.0 | https://github.com/jonasbb/serde_with/ |
| serde_with_macros | 3.20.0 | MIT OR Apache-2.0 | https://github.com/jonasbb/serde_with/ |
| serialize-to-javascript | 0.1.2 | MIT OR Apache-2.0 | https://github.com/chippers/serialize-to-javascript |
| serialize-to-javascript-impl | 0.1.2 | MIT OR Apache-2.0 | https://github.com/chippers/serialize-to-javascript |
| servo_arc | 0.4.3 | MIT OR Apache-2.0 | https://github.com/servo/stylo |
| sha1 | 0.10.6 | MIT OR Apache-2.0 | https://github.com/RustCrypto/hashes |
| sha2 | 0.10.9 | MIT OR Apache-2.0 | https://github.com/RustCrypto/hashes |
| shared_child | 1.1.1 | MIT | https://github.com/oconnor663/shared_child.rs |
| sigchld | 0.2.4 | MIT | https://github.com/oconnor663/sigchld.rs |
| signal-hook | 0.3.18 | Apache-2.0/MIT | https://github.com/vorner/signal-hook |
| signal-hook-registry | 1.4.8 | MIT OR Apache-2.0 | https://github.com/vorner/signal-hook |
| simd-adler32 | 0.3.9 | MIT | https://github.com/mcountryman/simd-adler32 |
| simd_cesu8 | 1.1.1 | Apache-2.0 OR MIT | https://github.com/seancroach/simd_cesu8 |
| simdutf8 | 0.1.5 | MIT OR Apache-2.0 | https://github.com/rusticstuff/simdutf8 |
| siphasher | 1.0.3 | MIT/Apache-2.0 | https://github.com/jedisct1/rust-siphash |
| slab | 0.4.12 | MIT | https://github.com/tokio-rs/slab |
| smallvec | 1.15.1 | MIT OR Apache-2.0 | https://github.com/servo/rust-smallvec |
| socket2 | 0.6.3 | MIT OR Apache-2.0 | https://github.com/rust-lang/socket2 |
| softbuffer | 0.4.8 | MIT OR Apache-2.0 | https://github.com/rust-windowing/softbuffer |
| soup3 | 0.5.0 | MIT | https://gitlab.gnome.org/World/Rust/soup3-rs |
| soup3-sys | 0.5.0 | MIT | https://gitlab.gnome.org/World/Rust/soup3-rs |
| stable_deref_trait | 1.2.1 | MIT OR Apache-2.0 | https://github.com/storyyeller/stable_deref_trait |
| static_assertions | 1.1.0 | MIT OR Apache-2.0 | https://github.com/nvzqz/static-assertions-rs |
| string_cache | 0.9.0 | MIT OR Apache-2.0 | https://github.com/servo/string-cache |
| strsim | 0.11.1 | MIT | https://github.com/rapidfuzz/strsim-rs |
| subtle | 2.6.1 | BSD-3-Clause | https://github.com/dalek-cryptography/subtle |
| swift-rs | 1.0.7 | MIT OR Apache-2.0 | https://github.com/Brendonovich/swift-rs |
| syn | 1.0.109 | MIT OR Apache-2.0 | https://github.com/dtolnay/syn |
| syn | 2.0.117 | MIT OR Apache-2.0 | https://github.com/dtolnay/syn |
| sync_wrapper | 1.0.2 | Apache-2.0 | https://github.com/Actyx/sync_wrapper |
| synstructure | 0.13.2 | MIT | https://github.com/mystor/synstructure |
| tao | 0.35.2 | Apache-2.0 | https://github.com/tauri-apps/tao |
| tao-macros | 0.1.3 | MIT OR Apache-2.0 | https://github.com/tauri-apps/tao |
| tar | 0.4.45 | MIT OR Apache-2.0 | https://github.com/alexcrichton/tar-rs |
| tauri | 2.11.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-codegen | 2.6.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-macros | 2.6.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-plugin-notification | 2.3.3 | Apache-2.0 OR MIT | https://github.com/tauri-apps/plugins-workspace |
| tauri-plugin-shell | 2.3.5 | Apache-2.0 OR MIT | https://github.com/tauri-apps/plugins-workspace |
| tauri-plugin-updater | 2.10.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/plugins-workspace |
| tauri-runtime | 2.11.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-runtime-wry | 2.11.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-utils | 2.9.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri |
| tauri-winrt-notification | 0.7.2 | MIT OR Apache-2.0 | https://github.com/tauri-apps/winrt-notification |
| tempfile | 3.27.0 | MIT OR Apache-2.0 | https://github.com/Stebalien/tempfile |
| tendril | 0.5.0 | MIT OR Apache-2.0 | https://github.com/servo/html5ever |
| thiserror | 1.0.69 | MIT OR Apache-2.0 | https://github.com/dtolnay/thiserror |
| thiserror | 2.0.18 | MIT OR Apache-2.0 | https://github.com/dtolnay/thiserror |
| thiserror-impl | 1.0.69 | MIT OR Apache-2.0 | https://github.com/dtolnay/thiserror |
| thiserror-impl | 2.0.18 | MIT OR Apache-2.0 | https://github.com/dtolnay/thiserror |
| time | 0.3.47 | MIT OR Apache-2.0 | https://github.com/time-rs/time |
| time-core | 0.1.8 | MIT OR Apache-2.0 | https://github.com/time-rs/time |
| time-macros | 0.2.27 | MIT OR Apache-2.0 | https://github.com/time-rs/time |
| tinystr | 0.8.3 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| tinyvec | 1.11.0 | Zlib OR Apache-2.0 OR MIT | https://github.com/Lokathor/tinyvec |
| tinyvec_macros | 0.1.1 | MIT OR Apache-2.0 OR Zlib | https://github.com/Soveu/tinyvec_macros |
| tokio | 1.52.3 | MIT | https://github.com/tokio-rs/tokio |
| tokio-macros | 2.7.0 | MIT | https://github.com/tokio-rs/tokio |
| tokio-rustls | 0.26.4 | MIT OR Apache-2.0 | https://github.com/rustls/tokio-rustls |
| tokio-util | 0.7.18 | MIT | https://github.com/tokio-rs/tokio |
| toml | 1.1.2+spec-1.1.0 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_datetime | 0.6.3 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_datetime | 1.1.1+spec-1.1.0 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_edit | 0.19.15 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_edit | 0.20.2 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_edit | 0.25.11+spec-1.1.0 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_parser | 1.1.2+spec-1.1.0 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| toml_writer | 1.1.1+spec-1.1.0 | MIT OR Apache-2.0 | https://github.com/toml-rs/toml |
| tower | 0.5.3 | MIT | https://github.com/tower-rs/tower |
| tower-http | 0.6.10 | MIT | https://github.com/tower-rs/tower-http |
| tower-layer | 0.3.3 | MIT | https://github.com/tower-rs/tower |
| tower-service | 0.3.3 | MIT | https://github.com/tower-rs/tower |
| tracing | 0.1.44 | MIT | https://github.com/tokio-rs/tracing |
| tracing-attributes | 0.1.31 | MIT | https://github.com/tokio-rs/tracing |
| tracing-core | 0.1.36 | MIT | https://github.com/tokio-rs/tracing |
| tray-icon | 0.23.1 | MIT OR Apache-2.0 | https://github.com/tauri-apps/tray-icon |
| try-lock | 0.2.5 | MIT | https://github.com/seanmonstar/try-lock |
| typeid | 1.0.3 | MIT OR Apache-2.0 | https://github.com/dtolnay/typeid |
| typenum | 1.20.0 | MIT OR Apache-2.0 | https://github.com/paholg/typenum |
| uds_windows | 1.2.1 | MIT | https://github.com/haraldh/rust_uds_windows |
| unic-char-property | 0.9.0 | MIT/Apache-2.0 | https://github.com/open-i18n/rust-unic/ |
| unic-char-range | 0.9.0 | MIT/Apache-2.0 | https://github.com/open-i18n/rust-unic/ |
| unic-common | 0.9.0 | MIT/Apache-2.0 | https://github.com/open-i18n/rust-unic/ |
| unic-ucd-ident | 0.9.0 | MIT/Apache-2.0 | https://github.com/open-i18n/rust-unic/ |
| unic-ucd-version | 0.9.0 | MIT/Apache-2.0 | https://github.com/open-i18n/rust-unic/ |
| unicode-ident | 1.0.24 | (MIT OR Apache-2.0) AND Unicode-3.0 | https://github.com/dtolnay/unicode-ident |
| unicode-segmentation | 1.13.2 | MIT OR Apache-2.0 | https://github.com/unicode-rs/unicode-segmentation |
| unicode-xid | 0.2.6 | MIT OR Apache-2.0 | https://github.com/unicode-rs/unicode-xid |
| untrusted | 0.9.0 | ISC | https://github.com/briansmith/untrusted |
| url | 2.5.8 | MIT OR Apache-2.0 | https://github.com/servo/rust-url |
| urlpattern | 0.3.0 | MIT | https://github.com/denoland/rust-urlpattern |
| utf-8 | 0.7.6 | MIT OR Apache-2.0 | https://github.com/SimonSapin/rust-utf8 |
| utf8_iter | 1.0.4 | Apache-2.0 OR MIT | https://github.com/hsivonen/utf8_iter |
| uuid | 1.23.1 | Apache-2.0 OR MIT | https://github.com/uuid-rs/uuid |
| walkdir | 2.5.0 | Unlicense/MIT | https://github.com/BurntSushi/walkdir |
| want | 0.3.1 | MIT | https://github.com/seanmonstar/want |
| wasi | 0.11.1+wasi-snapshot-preview1 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasi |
| wasip2 | 1.0.3+wasi-0.2.9 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasi-rs |
| wasip3 | 0.4.0+wasi-0.3.0-rc-2026-01-06 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasi-rs |
| wasm-bindgen | 0.2.121 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen |
| wasm-bindgen-futures | 0.4.71 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/futures |
| wasm-bindgen-macro | 0.2.121 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/macro |
| wasm-bindgen-macro-support | 0.2.121 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/macro-support |
| wasm-bindgen-shared | 0.2.121 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/shared |
| wasm-encoder | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasm-tools/tree/main/crates/wasm-encoder |
| wasm-metadata | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasm-tools/tree/main/crates/wasm-metadata |
| wasm-streams | 0.5.0 | MIT OR Apache-2.0 | https://github.com/MattiasBuelens/wasm-streams/ |
| wasmparser | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasm-tools/tree/main/crates/wasmparser |
| web_atoms | 0.2.4 | MIT OR Apache-2.0 | https://github.com/servo/html5ever |
| web-sys | 0.3.98 | MIT OR Apache-2.0 | https://github.com/wasm-bindgen/wasm-bindgen/tree/master/crates/web-sys |
| webkit2gtk | 2.0.2 | MIT | https://github.com/tauri-apps/webkit2gtk-rs |
| webkit2gtk-sys | 2.0.2 | MIT | https://github.com/tauri-apps/webkit2gtk-rs |
| webpki-root-certs | 1.0.7 | CDLA-Permissive-2.0 | https://github.com/rustls/webpki-roots |
| webview2-com | 0.38.2 | MIT | https://github.com/wravery/webview2-rs |
| webview2-com-macros | 0.8.1 | MIT | https://github.com/wravery/webview2-rs |
| webview2-com-sys | 0.38.2 | MIT | https://github.com/wravery/webview2-rs |
| winapi | 0.3.9 | MIT/Apache-2.0 | https://github.com/retep998/winapi-rs |
| winapi-i686-pc-windows-gnu | 0.4.0 | MIT/Apache-2.0 | https://github.com/retep998/winapi-rs |
| winapi-util | 0.1.11 | Unlicense OR MIT | https://github.com/BurntSushi/winapi-util |
| winapi-x86_64-pc-windows-gnu | 0.4.0 | MIT/Apache-2.0 | https://github.com/retep998/winapi-rs |
| window-vibrancy | 0.6.0 | Apache-2.0 OR MIT | https://github.com/tauri-apps/tauri-plugin-vibrancy |
| windows | 0.61.3 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_gnullvm | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_gnullvm | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_gnullvm | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_msvc | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_msvc | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_aarch64_msvc | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-collections | 0.2.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-core | 0.61.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-core | 0.62.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-future | 0.2.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_gnu | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_gnu | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_gnu | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_gnullvm | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_gnullvm | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_msvc | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_msvc | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_i686_msvc | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-implement | 0.60.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-interface | 0.59.3 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-link | 0.1.3 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-link | 0.2.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-numerics | 0.2.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-result | 0.3.4 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-result | 0.4.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-strings | 0.4.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-strings | 0.5.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-sys | 0.45.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-sys | 0.52.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-sys | 0.59.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-sys | 0.60.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-sys | 0.61.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-targets | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-targets | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-targets | 0.53.5 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-threading | 0.1.0 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows-version | 0.1.7 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnu | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnu | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnu | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnullvm | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnullvm | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_gnullvm | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_msvc | 0.42.2 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_msvc | 0.52.6 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| windows_x86_64_msvc | 0.53.1 | MIT OR Apache-2.0 | https://github.com/microsoft/windows-rs |
| winnow | 0.5.40 | MIT | https://github.com/winnow-rs/winnow |
| winnow | 1.0.2 | MIT | https://github.com/winnow-rs/winnow |
| wit-bindgen | 0.51.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wit-bindgen |
| wit-bindgen | 0.57.1 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wit-bindgen |
| wit-bindgen-core | 0.51.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wit-bindgen |
| wit-bindgen-rust | 0.51.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wit-bindgen |
| wit-bindgen-rust-macro | 0.51.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wit-bindgen |
| wit-component | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasm-tools/tree/main/crates/wit-component |
| wit-parser | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | https://github.com/bytecodealliance/wasm-tools/tree/main/crates/wit-parser |
| writeable | 0.6.3 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| wry | 0.55.1 | Apache-2.0 OR MIT | https://github.com/tauri-apps/wry |
| x11 | 2.21.0 | MIT | https://github.com/AltF02/x11-rs.git |
| x11-dl | 2.21.0 | MIT | https://github.com/AltF02/x11-rs.git |
| xattr | 1.6.1 | MIT OR Apache-2.0 | https://github.com/Stebalien/xattr |
| xdg-home | 1.3.0 | MIT | https://github.com/zeenix/xdg-home |
| yoke | 0.8.2 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| yoke-derive | 0.8.2 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zbus | 4.4.0 | MIT | https://github.com/dbus2/zbus/ |
| zbus | 5.15.0 | MIT | https://github.com/z-galaxy/zbus/ |
| zbus_macros | 4.4.0 | MIT | https://github.com/dbus2/zbus/ |
| zbus_macros | 5.15.0 | MIT | https://github.com/z-galaxy/zbus/ |
| zbus_names | 3.0.0 | MIT | https://github.com/dbus2/zbus/ |
| zbus_names | 4.3.2 | MIT | https://github.com/z-galaxy/zbus/ |
| zerocopy | 0.8.48 | BSD-2-Clause OR Apache-2.0 OR MIT | https://github.com/google/zerocopy |
| zerocopy-derive | 0.8.48 | BSD-2-Clause OR Apache-2.0 OR MIT | https://github.com/google/zerocopy |
| zerofrom | 0.1.8 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zerofrom-derive | 0.1.7 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zeroize | 1.8.2 | Apache-2.0 OR MIT | https://github.com/RustCrypto/utils |
| zeroize_derive | 1.4.3 | Apache-2.0 OR MIT | https://github.com/RustCrypto/utils/tree/master/zeroize/derive |
| zerotrie | 0.2.4 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zerovec | 0.11.6 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zerovec-derive | 0.11.3 | Unicode-3.0 | https://github.com/unicode-org/icu4x |
| zip | 4.6.1 | MIT | https://github.com/zip-rs/zip2.git |
| zmij | 1.0.21 | MIT | https://github.com/dtolnay/zmij |
| zvariant | 4.2.0 | MIT | https://github.com/dbus2/zbus/ |
| zvariant | 5.11.0 | MIT | https://github.com/z-galaxy/zbus/ |
| zvariant_derive | 4.2.0 | MIT | https://github.com/dbus2/zbus/ |
| zvariant_derive | 5.11.0 | MIT | https://github.com/z-galaxy/zbus/ |
| zvariant_utils | 2.1.0 | MIT | https://github.com/dbus2/zbus/ |
| zvariant_utils | 3.3.1 | MIT | https://github.com/z-galaxy/zbus/ |

_Note on `r-efi`: flagged by the Stage D scan because its licence string contains "LGPL", but it is an OR-choice (MIT/Apache-2.0 selectable without LGPL obligations) reachable only via `getrandom`'s UEFI-target edge, which is never active in a macOS/Windows/Linux desktop build — see DECISIONS §5.3._

## Section C — Not resolved

None. The four packages the Stage D scan flagged with empty registry licence metadata (`caio`, `fredapi`, `peewee`, `httpxthrottlecache`) were each resolved from their own shipped `LICENSE`/`COPYING` file in the relevant venv's dist-info (see DECISIONS §5.3); all four are permissive (Apache-2.0 or MIT) and appear in Section B above.

## Appendix — full licence texts

Each text below is taken verbatim from a package's own shipped `LICENSE` file in one of the inspected venvs (never reconstructed from memory), and covers every package above under the same SPDX id.

### AGPL-3.0

_Source: sec-edgar-mcp 1.0.8 (vysted-sec-edgar-mcp-sidecar)'s own LICENSE file._

```
GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU Affero General Public License is a free, copyleft license for
software and other kinds of works, specifically designed to ensure
cooperation with the community in the case of network server software.

  The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
our General Public Licenses are intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
them if you wish), that you receive source code or can get it if you
want it, that you can change the software or use pieces of it in new
free programs, and that you know you can do these things.

  Developers that use our General Public Licenses protect your rights
with two steps: (1) assert copyright on the software, and (2) offer
you this License which gives you legal permission to copy, distribute
and/or modify the software.

  A secondary benefit of defending all users' freedom is that
improvements made in alternate versions of the program, if they
receive widespread use, become available for other developers to
incorporate.  Many developers of free software are heartened and
encouraged by the resulting cooperation.  However, in the case of
software used on network servers, this result may fail to come about.
The GNU General Public License permits making a modified version and
letting the public access it on a server without ever releasing its
source code to the public.

  The GNU Affero General Public License is designed specifically to
ensure that, in such cases, the modified source code becomes available
to the community.  It requires the operator of a network server to
provide the source code of the modified version running there to the
users of that server.  Therefore, public use of a modified version, on
a publicly accessible server, gives the public access to the source
code of the modified version.

  An older license, called the Affero General Public License and
published by Affero, was designed to accomplish similar goals.  This is
a different license, not a version of the Affero GPL, but Affero has
released a new version of the Affero GPL which permits relicensing under
this license.

  The precise terms and conditions for copying, distribution and
modification follow.

                       TERMS AND CONDITIONS

  0. Definitions.

  "This License" refers to version 3 of the GNU Affero General Public License.

  "Copyright" also means copyright-like laws that apply to other kinds of
works, such as semiconductor masks.

  "The Program" refers to any copyrightable work licensed under this
License.  Each licensee is addressed as "you".  "Licensees" and
"recipients" may be individuals or organizations.

  To "modify" a work means to copy from or adapt all or part of the work
in a fashion requiring copyright permission, other than the making of an
exact copy.  The resulting work is called a "modified version" of the
earlier work or a work "based on" the earlier work.

  A "covered work" means either the unmodified Program or a work based
on the Program.

  To "propagate" a work means to do anything with it that, without
permission, would make you directly or secondarily liable for
infringement under applicable copyright law, except executing it on a
computer or modifying a private copy.  Propagation includes copying,
distribution (with or without modification), making available to the
public, and in some countries other activities as well.

  To "convey" a work means any kind of propagation that enables other
parties to make or receive copies.  Mere interaction with a user through
a computer network, with no transfer of a copy, is not conveying.

  An interactive user interface displays "Appropriate Legal Notices"
to the extent that it includes a convenient and prominently visible
feature that (1) displays an appropriate copyright notice, and (2)
tells the user that there is no warranty for the work (except to the
extent that warranties are provided), that licensees may convey the
work under this License, and how to view a copy of this License.  If
the interface presents a list of user commands or options, such as a
menu, a prominent item in the list meets this criterion.

  1. Source Code.

  The "source code" for a work means the preferred form of the work
for making modifications to it.  "Object code" means any non-source
form of a work.

  A "Standard Interface" means an interface that either is an official
standard defined by a recognized standards body, or, in the case of
interfaces specified for a particular programming language, one that
is widely used among developers working in that language.

  The "System Libraries" of an executable work include anything, other
than the work as a whole, that (a) is included in the normal form of
packaging a Major Component, but which is not part of that Major
Component, and (b) serves only to enable use of the work with that
Major Component, or to implement a Standard Interface for which an
implementation is available to the public in source code form.  A
"Major Component", in this context, means a major essential component
(kernel, window system, and so on) of the specific operating system
(if any) on which the executable work runs, or a compiler used to
produce the work, or an object code interpreter used to run it.

  The "Corresponding Source" for a work in object code form means all
the source code needed to generate, install, and (for an executable
work) run the object code and to modify the work, including scripts to
control those activities.  However, it does not include the work's
System Libraries, or general-purpose tools or generally available free
programs which are used unmodified in performing those activities but
which are not part of the work.  For example, Corresponding Source
includes interface definition files associated with source files for
the work, and the source code for shared libraries and dynamically
linked subprograms that the work is specifically designed to require,
such as by intimate data communication or control flow between those
subprograms and other parts of the work.

  The Corresponding Source need not include anything that users
can regenerate automatically from other parts of the Corresponding
Source.

  The Corresponding Source for a work in source code form is that
same work.

  2. Basic Permissions.

  All rights granted under this License are granted for the term of
copyright on the Program, and are irrevocable provided the stated
conditions are met.  This License explicitly affirms your unlimited
permission to run the unmodified Program.  The output from running a
covered work is covered by this License only if the output, given its
content, constitutes a covered work.  This License acknowledges your
rights of fair use or other equivalent, as provided by copyright law.

  You may make, run and propagate covered works that you do not
convey, without conditions so long as your license otherwise remains
in force.  You may convey covered works to others for the sole purpose
of having them make modifications exclusively for you, or provide you
with facilities for running those works, provided that you comply with
the terms of this License in conveying all material for which you do
not control copyright.  Those thus making or running the covered works
for you must do so exclusively on your behalf, under your direction
and control, on terms that prohibit them from making any copies of
your copyrighted material outside their relationship with you.

  Conveying under any other circumstances is permitted solely under
the conditions stated below.  Sublicensing is not allowed; section 10
makes it unnecessary.

  3. Protecting Users' Legal Rights From Anti-Circumvention Law.

  No covered work shall be deemed part of an effective technological
measure under any applicable law fulfilling obligations under article
11 of the WIPO copyright treaty adopted on 20 December 1996, or
similar laws prohibiting or restricting circumvention of such
measures.

  When you convey a covered work, you waive any legal power to forbid
circumvention of technological measures to the extent such circumvention
is effected by exercising rights under this License with respect to
the covered work, and you disclaim any intention to limit operation or
modification of the work as a means of enforcing, against the work's
users, your or third parties' legal rights to forbid circumvention of
technological measures.

  4. Conveying Verbatim Copies.

  You may convey verbatim copies of the Program's source code as you
receive it, in any medium, provided that you conspicuously and
appropriately publish on each copy an appropriate copyright notice;
keep intact all notices stating that this License and any
non-permissive terms added in accord with section 7 apply to the code;
keep intact all notices of the absence of any warranty; and give all
recipients a copy of this License along with the Program.

  You may charge any price or no price for each copy that you convey,
and you may offer support or warranty protection for a fee.

  5. Conveying Modified Source Versions.

  You may convey a work based on the Program, or the modifications to
produce it from the Program, in the form of source code under the
terms of section 4, provided that you also meet all of these conditions:

    a) The work must carry prominent notices stating that you modified
    it, and giving a relevant date.

    b) The work must carry prominent notices stating that it is
    released under this License and any conditions added under section
    7.  This requirement modifies the requirement in section 4 to
    "keep intact all notices".

    c) You must license the entire work, as a whole, under this
    License to anyone who comes into possession of a copy.  This
    License will therefore apply, along with any applicable section 7
    additional terms, to the whole of the work, and all its parts,
    regardless of how they are packaged.  This License gives no
    permission to license the work in any other way, but it does not
    invalidate such permission if you have separately received it.

    d) If the work has interactive user interfaces, each must display
    Appropriate Legal Notices; however, if the Program has interactive
    interfaces that do not display Appropriate Legal Notices, your
    work need not make them do so.

  A compilation of a covered work with other separate and independent
works, which are not by their nature extensions of the covered work,
and which are not combined with it such as to form a larger program,
in or on a volume of a storage or distribution medium, is called an
"aggregate" if the compilation and its resulting copyright are not
used to limit the access or legal rights of the compilation's users
beyond what the individual works permit.  Inclusion of a covered work
in an aggregate does not cause this License to apply to the other
parts of the aggregate.

  6. Conveying Non-Source Forms.

  You may convey a covered work in object code form under the terms
of sections 4 and 5, provided that you also convey the
machine-readable Corresponding Source under the terms of this License,
in one of these ways:

    a) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by the
    Corresponding Source fixed on a durable physical medium
    customarily used for software interchange.

    b) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by a
    written offer, valid for at least three years and valid for as
    long as you offer spare parts or customer support for that product
    model, to give anyone who possesses the object code either (1) a
    copy of the Corresponding Source for all the software in the
    product that is covered by this License, on a durable physical
    medium customarily used for software interchange, for a price no
    more than your reasonable cost of physically performing this
    conveying of source, or (2) access to copy the
    Corresponding Source from a network server at no charge.

    c) Convey individual copies of the object code with a copy of the
    written offer to provide the Corresponding Source.  This
    alternative is allowed only occasionally and noncommercially, and
    only if you received the object code with such an offer, in accord
    with subsection 6b.

    d) Convey the object code by offering access from a designated
    place (gratis or for a charge), and offer equivalent access to the
    Corresponding Source in the same way through the same place at no
    further charge.  You need not require recipients to copy the
    Corresponding Source along with the object code.  If the place to
    copy the object code is a network server, the Corresponding Source
    may be on a different server (operated by you or a third party)
    that supports equivalent copying facilities, provided you maintain
    clear directions next to the object code saying where to find the
    Corresponding Source.  Regardless of what server hosts the
    Corresponding Source, you remain obligated to ensure that it is
    available for as long as needed to satisfy these requirements.

    e) Convey the object code using peer-to-peer transmission, provided
    you inform other peers where the object code and Corresponding
    Source of the work are being offered to the general public at no
    charge under subsection 6d.

  A separable portion of the object code, whose source code is excluded
from the Corresponding Source as a System Library, need not be
included in conveying the object code work.

  A "User Product" is either (1) a "consumer product", which means any
tangible personal property which is normally used for personal, family,
or household purposes, or (2) anything designed or sold for incorporation
into a dwelling.  In determining whether a product is a consumer product,
doubtful cases shall be resolved in favor of coverage.  For a particular
product received by a particular user, "normally used" refers to a
typical or common use of that class of product, regardless of the status
of the particular user or of the way in which the particular user
actually uses, or expects or is expected to use, the product.  A product
is a consumer product regardless of whether the product has substantial
commercial, industrial or non-consumer uses, unless such uses represent
the only significant mode of use of the product.

  "Installation Information" for a User Product means any methods,
procedures, authorization keys, or other information required to install
and execute modified versions of a covered work in that User Product from
a modified version of its Corresponding Source.  The information must
suffice to ensure that the continued functioning of the modified object
code is in no case prevented or interfered with solely because
modification has been made.

  If you convey an object code work under this section in, or with, or
specifically for use in, a User Product, and the conveying occurs as
part of a transaction in which the right of possession and use of the
User Product is transferred to the recipient in perpetuity or for a
fixed term (regardless of how the transaction is characterized), the
Corresponding Source conveyed under this section must be accompanied
by the Installation Information.  But this requirement does not apply
if neither you nor any third party retains the ability to install
modified object code on the User Product (for example, the work has
been installed in ROM).

  The requirement to provide Installation Information does not include a
requirement to continue to provide support service, warranty, or updates
for a work that has been modified or installed by the recipient, or for
the User Product in which it has been modified or installed.  Access to a
network may be denied when the modification itself materially and
adversely affects the operation of the network or violates the rules and
protocols for communication across the network.

  Corresponding Source conveyed, and Installation Information provided,
in accord with this section must be in a format that is publicly
documented (and with an implementation available to the public in
source code form), and must require no special password or key for
unpacking, reading or copying.

  7. Additional Terms.

  "Additional permissions" are terms that supplement the terms of this
License by making exceptions from one or more of its conditions.
Additional permissions that are applicable to the entire Program shall
be treated as though they were included in this License, to the extent
that they are valid under applicable law.  If additional permissions
apply only to part of the Program, that part may be used separately
under those permissions, but the entire Program remains governed by
this License without regard to the additional permissions.

  When you convey a copy of a covered work, you may at your option
remove any additional permissions from that copy, or from any part of
it.  (Additional permissions may be written to require their own
removal in certain cases when you modify the work.)  You may place
additional permissions on material, added by you to a covered work,
for which you have or can give appropriate copyright permission.

  Notwithstanding any other provision of this License, for material you
add to a covered work, you may (if authorized by the copyright holders of
that material) supplement the terms of this License with terms:

    a) Disclaiming warranty or limiting liability differently from the
    terms of sections 15 and 16 of this License; or

    b) Requiring preservation of specified reasonable legal notices or
    author attributions in that material or in the Appropriate Legal
    Notices displayed by works containing it; or

    c) Prohibiting misrepresentation of the origin of that material, or
    requiring that modified versions of such material be marked in
    reasonable ways as different from the original version; or

    d) Limiting the use for publicity purposes of names of licensors or
    authors of the material; or

    e) Declining to grant rights under trademark law for use of some
    trade names, trademarks, or service marks; or

    f) Requiring indemnification of licensors and authors of that
    material by anyone who conveys the material (or modified versions of
    it) with contractual assumptions of liability to the recipient, for
    any liability that these contractual assumptions directly impose on
    those licensors and authors.

  All other non-permissive additional terms are considered "further
restrictions" within the meaning of section 10.  If the Program as you
received it, or any part of it, contains a notice stating that it is
governed by this License along with a term that is a further
restriction, you may remove that term.  If a license document contains
a further restriction but permits relicensing or conveying under this
License, you may add to a covered work material governed by the terms
of that license document, provided that the further restriction does
not survive such relicensing or conveying.

  If you add terms to a covered work in accord with this section, you
must place, in the relevant source files, a statement of the
additional terms that apply to those files, or a notice indicating
where to find the applicable terms.

  Additional terms, permissive or non-permissive, may be stated in the
form of a separately written license, or stated as exceptions;
the above requirements apply either way.

  8. Termination.

  You may not propagate or modify a covered work except as expressly
provided under this License.  Any attempt otherwise to propagate or
modify it is void, and will automatically terminate your rights under
this License (including any patent licenses granted under the third
paragraph of section 11).

  However, if you cease all violation of this License, then your
license from a particular copyright holder is reinstated (a)
provisionally, unless and until the copyright holder explicitly and
finally terminates your license, and (b) permanently, if the copyright
holder fails to notify you of the violation by some reasonable means
prior to 60 days after the cessation.

  Moreover, your license from a particular copyright holder is
reinstated permanently if the copyright holder notifies you of the
violation by some reasonable means, this is the first time you have
received notice of violation of this License (for any work) from that
copyright holder, and you cure the violation prior to 30 days after
your receipt of the notice.

  Termination of your rights under this section does not terminate the
licenses of parties who have received copies or rights from you under
this License.  If your rights have been terminated and not permanently
reinstated, you do not qualify to receive new licenses for the same
material under section 10.

  9. Acceptance Not Required for Having Copies.

  You are not required to accept this License in order to receive or
run a copy of the Program.  Ancillary propagation of a covered work
occurring solely as a consequence of using peer-to-peer transmission
to receive a copy likewise does not require acceptance.  However,
nothing other than this License grants you permission to propagate or
modify any covered work.  These actions infringe copyright if you do
not accept this License.  Therefore, by modifying or propagating a
covered work, you indicate your acceptance of this License to do so.

  10. Automatic Licensing of Downstream Recipients.

  Each time you convey a covered work, the recipient automatically
receives a license from the original licensors, to run, modify and
propagate that work, subject to this License.  You are not responsible
for enforcing compliance by third parties with this License.

  An "entity transaction" is a transaction transferring control of an
organization, or substantially all assets of one, or subdividing an
organization, or merging organizations.  If propagation of a covered
work results from an entity transaction, each party to that
transaction who receives a copy of the work also receives whatever
licenses to the work the party's predecessor in interest had or could
give under the previous paragraph, plus a right to possession of the
Corresponding Source of the work from the predecessor in interest, if
the predecessor has it or can get it with reasonable efforts.

  You may not impose any further restrictions on the exercise of the
rights granted or affirmed under this License.  For example, you may
not impose a license fee, royalty, or other charge for exercise of
rights granted under this License, and you may not initiate litigation
(including a cross-claim or counterclaim in a lawsuit) alleging that
any patent claim is infringed by making, using, selling, offering for
sale, or importing the Program or any portion of it.

  11. Patents.

  A "contributor" is a copyright holder who authorizes use under this
License of the Program or a work on which the Program is based.  The
work thus licensed is called the contributor's "contributor version".

  A contributor's "essential patent claims" are all patent claims
owned or controlled by the contributor, whether already acquired or
hereafter acquired, that would be infringed by some manner, permitted
by this License, of making, using, or selling its contributor version,
but do not include claims that would be infringed only as a
consequence of further modification of the contributor version.  For
purposes of this definition, "control" includes the right to grant
patent sublicenses in a manner consistent with the requirements of
this License.

  Each contributor grants you a non-exclusive, worldwide, royalty-free
patent license under the contributor's essential patent claims, to
make, use, sell, offer for sale, import and otherwise run, modify and
propagate the contents of its contributor version.

  In the following three paragraphs, a "patent license" is any express
agreement or commitment, however denominated, not to enforce a patent
(such as an express permission to practice a patent or covenant not to
sue for patent infringement).  To "grant" such a patent license to a
party means to make such an agreement or commitment not to enforce a
patent against the party.

  If you convey a covered work, knowingly relying on a patent license,
and the Corresponding Source of the work is not available for anyone
to copy, free of charge and under the terms of this License, through a
publicly available network server or other readily accessible means,
then you must either (1) cause the Corresponding Source to be so
available, or (2) arrange to deprive yourself of the benefit of the
patent license for this particular work, or (3) arrange, in a manner
consistent with the requirements of this License, to extend the patent
license to downstream recipients.  "Knowingly relying" means you have
actual knowledge that, but for the patent license, your conveying the
covered work in a country, or your recipient's use of the covered work
in a country, would infringe one or more identifiable patents in that
country that you have reason to believe are valid.

  If, pursuant to or in connection with a single transaction or
arrangement, you convey, or propagate by procuring conveyance of, a
covered work, and grant a patent license to some of the parties
receiving the covered work authorizing them to use, propagate, modify
or convey a specific copy of the covered work, then the patent license
you grant is automatically extended to all recipients of the covered
work and works based on it.

  A patent license is "discriminatory" if it does not include within
the scope of its coverage, prohibits the exercise of, or is
conditioned on the non-exercise of one or more of the rights that are
specifically granted under this License.  You may not convey a covered
work if you are a party to an arrangement with a third party that is
in the business of distributing software, under which you make payment
to the third party based on the extent of your activity of conveying
the work, and under which the third party grants, to any of the
parties who would receive the covered work from you, a discriminatory
patent license (a) in connection with copies of the covered work
conveyed by you (or copies made from those copies), or (b) primarily
for and in connection with specific products or compilations that
contain the covered work, unless you entered into that arrangement,
or that patent license was granted, prior to 28 March 2007.

  Nothing in this License shall be construed as excluding or limiting
any implied license or other defenses to infringement that may
otherwise be available to you under applicable patent law.

  12. No Surrender of Others' Freedom.

  If conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot convey a
covered work so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you may
not convey it at all.  For example, if you agree to terms that obligate you
to collect a royalty for further conveying from those to whom you convey
the Program, the only way you could satisfy both those terms and this
License would be to refrain entirely from conveying the Program.

  13. Remote Network Interaction; Use with the GNU General Public License.

  Notwithstanding any other provision of this License, if you modify the
Program, your modified version must prominently offer all users
interacting with it remotely through a computer network (if your version
supports such interaction) an opportunity to receive the Corresponding
Source of your version by providing access to the Corresponding Source
from a network server at no charge, through some standard or customary
means of facilitating copying of software.  This Corresponding Source
shall include the Corresponding Source for any work covered by version 3
of the GNU General Public License that is incorporated pursuant to the
following paragraph.

  Notwithstanding any other provision of this License, you have
permission to link or combine any covered work with a work licensed
under version 3 of the GNU General Public License into a single
combined work, and to convey the resulting work.  The terms of this
License will continue to apply to the part which is the covered work,
but the work with which it is combined will remain governed by version
3 of the GNU General Public License.

  14. Revised Versions of this License.

  The Free Software Foundation may publish revised and/or new versions of
the GNU Affero General Public License from time to time.  Such new versions
will be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

  Each version is given a distinguishing version number.  If the
Program specifies that a certain numbered version of the GNU Affero General
Public License "or any later version" applies to it, you have the
option of following the terms and conditions either of that numbered
version or of any later version published by the Free Software
Foundation.  If the Program does not specify a version number of the
GNU Affero General Public License, you may choose any version ever published
by the Free Software Foundation.

  If the Program specifies that a proxy can decide which future
versions of the GNU Affero General Public License can be used, that proxy's
public statement of acceptance of a version permanently authorizes you
to choose that version for the Program.

  Later license versions may give you additional or different
permissions.  However, no additional obligations are imposed on any
author or copyright holder as a result of your choosing to follow a
later version.

  15. Disclaimer of Warranty.

  THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW.  EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY
OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

  16. Limitation of Liability.

  IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
SUCH DAMAGES.

  17. Interpretation of Sections 15 and 16.

  If the disclaimer of warranty and limitation of liability provided
above cannot be given local legal effect according to their terms,
reviewing courts shall apply local law that most closely approximates
an absolute waiver of all civil liability in connection with the
Program, unless a warranty or assumption of liability accompanies a
copy of the Program in return for a fee.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
state the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    sec-edgar-mcp — An MCP server for accessing and querying SEC EDGAR filings.
    Copyright (C) 2025  Stefano Amorelli

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

Also add information on how to contact you by electronic and paper mail.

  If your software can interact with users remotely through a computer
network, you should also make sure that it provides a way for users to
get its source.  For example, if your program is a web application, its
interface could display a "Source" link that leads users to an archive
of the code.  There are many ways you could offer source, and different
solutions will be better for different programs; see section 13 for the
specific requirements.

  You should also get your employer (if you work as a programmer) or school,
if any, to sign a "copyright disclaimer" for the program, if necessary.
For more information on this, and how to apply and follow the GNU AGPL, see
<https://www.gnu.org/licenses/>.
```

### GPL-2.0

_Source: Unidecode 1.4.0 (vysted-sec-edgar-mcp-sidecar)'s own LICENSE file._

```
GNU GENERAL PUBLIC LICENSE
                       Version 2, June 1991

 Copyright (C) 1989, 1991 Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The licenses for most software are designed to take away your
freedom to share and change it.  By contrast, the GNU General Public
License is intended to guarantee your freedom to share and change free
software--to make sure the software is free for all its users.  This
General Public License applies to most of the Free Software
Foundation's software and to any other program whose authors commit to
using it.  (Some other Free Software Foundation software is covered by
the GNU Lesser General Public License instead.)  You can apply it to
your programs, too.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
this service if you wish), that you receive source code or can get it
if you want it, that you can change the software or use pieces of it
in new free programs; and that you know you can do these things.

  To protect your rights, we need to make restrictions that forbid
anyone to deny you these rights or to ask you to surrender the rights.
These restrictions translate to certain responsibilities for you if you
distribute copies of the software, or if you modify it.

  For example, if you distribute copies of such a program, whether
gratis or for a fee, you must give the recipients all the rights that
you have.  You must make sure that they, too, receive or can get the
source code.  And you must show them these terms so they know their
rights.

  We protect your rights with two steps: (1) copyright the software, and
(2) offer you this license which gives you legal permission to copy,
distribute and/or modify the software.

  Also, for each author's protection and ours, we want to make certain
that everyone understands that there is no warranty for this free
software.  If the software is modified by someone else and passed on, we
want its recipients to know that what they have is not the original, so
that any problems introduced by others will not reflect on the original
authors' reputations.

  Finally, any free program is threatened constantly by software
patents.  We wish to avoid the danger that redistributors of a free
program will individually obtain patent licenses, in effect making the
program proprietary.  To prevent this, we have made it clear that any
patent must be licensed for everyone's free use or not licensed at all.

  The precise terms and conditions for copying, distribution and
modification follow.

                    GNU GENERAL PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. This License applies to any program or other work which contains
a notice placed by the copyright holder saying it may be distributed
under the terms of this General Public License.  The "Program", below,
refers to any such program or work, and a "work based on the Program"
means either the Program or any derivative work under copyright law:
that is to say, a work containing the Program or a portion of it,
either verbatim or with modifications and/or translated into another
language.  (Hereinafter, translation is included without limitation in
the term "modification".)  Each licensee is addressed as "you".

Activities other than copying, distribution and modification are not
covered by this License; they are outside its scope.  The act of
running the Program is not restricted, and the output from the Program
is covered only if its contents constitute a work based on the
Program (independent of having been made by running the Program).
Whether that is true depends on what the Program does.

  1. You may copy and distribute verbatim copies of the Program's
source code as you receive it, in any medium, provided that you
conspicuously and appropriately publish on each copy an appropriate
copyright notice and disclaimer of warranty; keep intact all the
notices that refer to this License and to the absence of any warranty;
and give any other recipients of the Program a copy of this License
along with the Program.

You may charge a fee for the physical act of transferring a copy, and
you may at your option offer warranty protection in exchange for a fee.

  2. You may modify your copy or copies of the Program or any portion
of it, thus forming a work based on the Program, and copy and
distribute such modifications or work under the terms of Section 1
above, provided that you also meet all of these conditions:

    a) You must cause the modified files to carry prominent notices
    stating that you changed the files and the date of any change.

    b) You must cause any work that you distribute or publish, that in
    whole or in part contains or is derived from the Program or any
    part thereof, to be licensed as a whole at no charge to all third
    parties under the terms of this License.

    c) If the modified program normally reads commands interactively
    when run, you must cause it, when started running for such
    interactive use in the most ordinary way, to print or display an
    announcement including an appropriate copyright notice and a
    notice that there is no warranty (or else, saying that you provide
    a warranty) and that users may redistribute the program under
    these conditions, and telling the user how to view a copy of this
    License.  (Exception: if the Program itself is interactive but
    does not normally print such an announcement, your work based on
    the Program is not required to print an announcement.)

These requirements apply to the modified work as a whole.  If
identifiable sections of that work are not derived from the Program,
and can be reasonably considered independent and separate works in
themselves, then this License, and its terms, do not apply to those
sections when you distribute them as separate works.  But when you
distribute the same sections as part of a whole which is a work based
on the Program, the distribution of the whole must be on the terms of
this License, whose permissions for other licensees extend to the
entire whole, and thus to each and every part regardless of who wrote it.

Thus, it is not the intent of this section to claim rights or contest
your rights to work written entirely by you; rather, the intent is to
exercise the right to control the distribution of derivative or
collective works based on the Program.

In addition, mere aggregation of another work not based on the Program
with the Program (or with a work based on the Program) on a volume of
a storage or distribution medium does not bring the other work under
the scope of this License.

  3. You may copy and distribute the Program (or a work based on it,
under Section 2) in object code or executable form under the terms of
Sections 1 and 2 above provided that you also do one of the following:

    a) Accompany it with the complete corresponding machine-readable
    source code, which must be distributed under the terms of Sections
    1 and 2 above on a medium customarily used for software interchange; or,

    b) Accompany it with a written offer, valid for at least three
    years, to give any third party, for a charge no more than your
    cost of physically performing source distribution, a complete
    machine-readable copy of the corresponding source code, to be
    distributed under the terms of Sections 1 and 2 above on a medium
    customarily used for software interchange; or,

    c) Accompany it with the information you received as to the offer
    to distribute corresponding source code.  (This alternative is
    allowed only for noncommercial distribution and only if you
    received the program in object code or executable form with such
    an offer, in accord with Subsection b above.)

The source code for a work means the preferred form of the work for
making modifications to it.  For an executable work, complete source
code means all the source code for all modules it contains, plus any
associated interface definition files, plus the scripts used to
control compilation and installation of the executable.  However, as a
special exception, the source code distributed need not include
anything that is normally distributed (in either source or binary
form) with the major components (compiler, kernel, and so on) of the
operating system on which the executable runs, unless that component
itself accompanies the executable.

If distribution of executable or object code is made by offering
access to copy from a designated place, then offering equivalent
access to copy the source code from the same place counts as
distribution of the source code, even though third parties are not
compelled to copy the source along with the object code.

  4. You may not copy, modify, sublicense, or distribute the Program
except as expressly provided under this License.  Any attempt
otherwise to copy, modify, sublicense or distribute the Program is
void, and will automatically terminate your rights under this License.
However, parties who have received copies, or rights, from you under
this License will not have their licenses terminated so long as such
parties remain in full compliance.

  5. You are not required to accept this License, since you have not
signed it.  However, nothing else grants you permission to modify or
distribute the Program or its derivative works.  These actions are
prohibited by law if you do not accept this License.  Therefore, by
modifying or distributing the Program (or any work based on the
Program), you indicate your acceptance of this License to do so, and
all its terms and conditions for copying, distributing or modifying
the Program or works based on it.

  6. Each time you redistribute the Program (or any work based on the
Program), the recipient automatically receives a license from the
original licensor to copy, distribute or modify the Program subject to
these terms and conditions.  You may not impose any further
restrictions on the recipients' exercise of the rights granted herein.
You are not responsible for enforcing compliance by third parties to
this License.

  7. If, as a consequence of a court judgment or allegation of patent
infringement or for any other reason (not limited to patent issues),
conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot
distribute so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you
may not distribute the Program at all.  For example, if a patent
license would not permit royalty-free redistribution of the Program by
all those who receive copies directly or indirectly through you, then
the only way you could satisfy both it and this License would be to
refrain entirely from distribution of the Program.

If any portion of this section is held invalid or unenforceable under
any particular circumstance, the balance of the section is intended to
apply and the section as a whole is intended to apply in other
circumstances.

It is not the purpose of this section to induce you to infringe any
patents or other property right claims or to contest validity of any
such claims; this section has the sole purpose of protecting the
integrity of the free software distribution system, which is
implemented by public license practices.  Many people have made
generous contributions to the wide range of software distributed
through that system in reliance on consistent application of that
system; it is up to the author/donor to decide if he or she is willing
to distribute software through any other system and a licensee cannot
impose that choice.

This section is intended to make thoroughly clear what is believed to
be a consequence of the rest of this License.

  8. If the distribution and/or use of the Program is restricted in
certain countries either by patents or by copyrighted interfaces, the
original copyright holder who places the Program under this License
may add an explicit geographical distribution limitation excluding
those countries, so that distribution is permitted only in or among
countries not thus excluded.  In such case, this License incorporates
the limitation as if written in the body of this License.

  9. The Free Software Foundation may publish revised and/or new versions
of the General Public License from time to time.  Such new versions will
be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

Each version is given a distinguishing version number.  If the Program
specifies a version number of this License which applies to it and "any
later version", you have the option of following the terms and conditions
either of that version or of any later version published by the Free
Software Foundation.  If the Program does not specify a version number of
this License, you may choose any version ever published by the Free Software
Foundation.

  10. If you wish to incorporate parts of the Program into other free
programs whose distribution conditions are different, write to the author
to ask for permission.  For software which is copyrighted by the Free
Software Foundation, write to the Free Software Foundation; we sometimes
make exceptions for this.  Our decision will be guided by the two goals
of preserving the free status of all derivatives of our free software and
of promoting the sharing and reuse of software generally.

                            NO WARRANTY

  11. BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO WARRANTY
FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW.  EXCEPT WHEN
OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES
PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED
OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.  THE ENTIRE RISK AS
TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.  SHOULD THE
PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING,
REPAIR OR CORRECTION.

  12. IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR
REDISTRIBUTE THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES,
INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING
OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED
TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY
YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER
PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE
POSSIBILITY OF SUCH DAMAGES.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
convey the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

Also add information on how to contact you by electronic and paper mail.

If the program is interactive, make it output a short notice like this
when it starts in an interactive mode:

    Gnomovision version 69, Copyright (C) year name of author
    Gnomovision comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.

The hypothetical commands `show w' and `show c' should show the appropriate
parts of the General Public License.  Of course, the commands you use may
be called something other than `show w' and `show c'; they could even be
mouse-clicks or menu items--whatever suits your program.

You should also get your employer (if you work as a programmer) or your
school, if any, to sign a "copyright disclaimer" for the program, if
necessary.  Here is a sample; alter the names:

  Yoyodyne, Inc., hereby disclaims all copyright interest in the program
  `Gnomovision' (which makes passes at compilers) written by James Hacker.

  <signature of Ty Coon>, 1 April 1989
  Ty Coon, President of Vice

This General Public License does not permit incorporating your program into
proprietary programs.  If your program is a subroutine library, you may
consider it more useful to permit linking proprietary applications with the
library.  If this is what you want to do, use the GNU Lesser General
Public License instead of this License.
```

### LGPL-3.0

_Source: frozendict 2.4.7 (vysted-openbb-mcp-sidecar)'s own LICENSE file._

```
GNU LESSER GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.


  This version of the GNU Lesser General Public License incorporates
the terms and conditions of version 3 of the GNU General Public
License, supplemented by the additional permissions listed below.

  0. Additional Definitions.

  As used herein, "this License" refers to version 3 of the GNU Lesser
General Public License, and the "GNU GPL" refers to version 3 of the GNU
General Public License.

  "The Library" refers to a covered work governed by this License,
other than an Application or a Combined Work as defined below.

  An "Application" is any work that makes use of an interface provided
by the Library, but which is not otherwise based on the Library.
Defining a subclass of a class defined by the Library is deemed a mode
of using an interface provided by the Library.

  A "Combined Work" is a work produced by combining or linking an
Application with the Library.  The particular version of the Library
with which the Combined Work was made is also called the "Linked
Version".

  The "Minimal Corresponding Source" for a Combined Work means the
Corresponding Source for the Combined Work, excluding any source code
for portions of the Combined Work that, considered in isolation, are
based on the Application, and not on the Linked Version.

  The "Corresponding Application Code" for a Combined Work means the
object code and/or source code for the Application, including any data
and utility programs needed for reproducing the Combined Work from the
Application, but excluding the System Libraries of the Combined Work.

  1. Exception to Section 3 of the GNU GPL.

  You may convey a covered work under sections 3 and 4 of this License
without being bound by section 3 of the GNU GPL.

  2. Conveying Modified Versions.

  If you modify a copy of the Library, and, in your modifications, a
facility refers to a function or data to be supplied by an Application
that uses the facility (other than as an argument passed when the
facility is invoked), then you may convey a copy of the modified
version:

   a) under this License, provided that you make a good faith effort to
   ensure that, in the event an Application does not supply the
   function or data, the facility still operates, and performs
   whatever part of its purpose remains meaningful, or

   b) under the GNU GPL, with none of the additional permissions of
   this License applicable to that copy.

  3. Object Code Incorporating Material from Library Header Files.

  The object code form of an Application may incorporate material from
a header file that is part of the Library.  You may convey such object
code under terms of your choice, provided that, if the incorporated
material is not limited to numerical parameters, data structure
layouts and accessors, or small macros, inline functions and templates
(ten or fewer lines in length), you do both of the following:

   a) Give prominent notice with each copy of the object code that the
   Library is used in it and that the Library and its use are
   covered by this License.

   b) Accompany the object code with a copy of the GNU GPL and this license
   document.

  4. Combined Works.

  You may convey a Combined Work under terms of your choice that,
taken together, effectively do not restrict modification of the
portions of the Library contained in the Combined Work and reverse
engineering for debugging such modifications, if you also do each of
the following:

   a) Give prominent notice with each copy of the Combined Work that
   the Library is used in it and that the Library and its use are
   covered by this License.

   b) Accompany the Combined Work with a copy of the GNU GPL and this license
   document.

   c) For a Combined Work that displays copyright notices during
   execution, include the copyright notice for the Library among
   these notices, as well as a reference directing the user to the
   copies of the GNU GPL and this license document.

   d) Do one of the following:

       0) Convey the Minimal Corresponding Source under the terms of this
       License, and the Corresponding Application Code in a form
       suitable for, and under terms that permit, the user to
       recombine or relink the Application with a modified version of
       the Linked Version to produce a modified Combined Work, in the
       manner specified by section 6 of the GNU GPL for conveying
       Corresponding Source.

       1) Use a suitable shared library mechanism for linking with the
       Library.  A suitable mechanism is one that (a) uses at run time
       a copy of the Library already present on the user's computer
       system, and (b) will operate properly with a modified version
       of the Library that is interface-compatible with the Linked
       Version.

   e) Provide Installation Information, but only if you would otherwise
   be required to provide such information under section 6 of the
   GNU GPL, and only to the extent that such information is
   necessary to install and execute a modified version of the
   Combined Work produced by recombining or relinking the
   Application with a modified version of the Linked Version. (If
   you use option 4d0, the Installation Information must accompany
   the Minimal Corresponding Source and Corresponding Application
   Code. If you use option 4d1, you must provide the Installation
   Information in the manner specified by section 6 of the GNU GPL
   for conveying Corresponding Source.)

  5. Combined Libraries.

  You may place library facilities that are a work based on the
Library side by side in a single library together with other library
facilities that are not Applications and are not covered by this
License, and convey such a combined library under terms of your
choice, if you do both of the following:

   a) Accompany the combined library with a copy of the same work based
   on the Library, uncombined with any other library facilities,
   conveyed under the terms of this License.

   b) Give prominent notice with the combined library that part of it
   is a work based on the Library, and explaining where to find the
   accompanying uncombined form of the same work.

  6. Revised Versions of the GNU Lesser General Public License.

  The Free Software Foundation may publish revised and/or new versions
of the GNU Lesser General Public License from time to time. Such new
versions will be similar in spirit to the present version, but may
differ in detail to address new problems or concerns.

  Each version is given a distinguishing version number. If the
Library as you received it specifies that a certain numbered version
of the GNU Lesser General Public License "or any later version"
applies to it, you have the option of following the terms and
conditions either of that published version or of any later version
published by the Free Software Foundation. If the Library as you
received it does not specify a version number of the GNU Lesser
General Public License, you may choose any version of the GNU Lesser
General Public License ever published by the Free Software Foundation.

  If the Library as you received it specifies that a proxy can decide
whether future versions of the GNU Lesser General Public License shall
apply, that proxy's public statement of acceptance of any version is
permanent authorization for you to choose that version for the
Library.
```

## Caveats

- Only this machine's (macOS/Apple Silicon) venvs and lockfiles were inspected — no Windows or Linux wheels were scanned, so a platform-conditional dependency resolving differently there would not show up here.
- Python bundled/dev-only scope is taken from the Stage D scan's Requires-Dist closure walk (DEPS_LICENCES.json), not recomputed by this script.
- This is a DRAFT for the operator to promote, correct, or reject — it draws no legal conclusion about licence compatibility.

