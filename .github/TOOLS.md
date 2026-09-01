# Release tooling

These Windows executables are used only by `.github/workflows/release.yml` and are excluded from the published mod archive.

## Origin in KyoHUD

The four original release-tool binaries were copied from Hugo Zink's [`PD2AutoUpdateExample`](https://github.com/morerokk/PD2AutoUpdateExample). Their SHA-256 hashes match that repository byte for byte. They entered KyoHUD in commit `4d00ab5`.

## `7za.exe`

- Purpose: build `latest.zip` on the Windows GitHub Actions runner.
- Upstream: the x64 `7za.exe` from the official [7-Zip Extra 19.00 archive](https://www.7-zip.org/a/7z1900-extra.7z).
- Copyright: Igor Pavlov, 1999-2019.
- License: GNU LGPL 2.1 or later; see [`7ZIP_LICENSE.txt`](7ZIP_LICENSE.txt).
- SHA-256: `8117e40ee7f824f63373a4f5625bb62749f69159d0c449b3ce2f35aad3b83549`

The official 7-Zip Extra readme states that `7za.exe` is standalone and does not use external DLL files. KyoHUD's workflow calls only `7za.exe`, so the copied `7za.dll` and `7zxa.dll` were unused and are not retained.

## `superblt_hash.py`

- Purpose: compute the SuperBLT directory hash written to the generated `meta.json`.
- Implementation: transparent, standard-library-only Python maintained in this repository.
- Verification: `.github/test_superblt_hash.py` contains fixed vectors captured from the former executable and checks both file and directory hashing plus CLI behavior.

The previous `hash.exe` was copied from `PD2AutoUpdateExample` and matched fragtrane's [`Python-SuperBLT-Hash-Calculator`](https://github.com/fragtrane/Python-SuperBLT-Hash-Calculator) version 1.0 exactly (`SHA-256: 78d08678e13b8daec1961491deca5e0f2e352d7d7f4a85a9d3c51ea34d88321a`). It was replaced because its upstream repository publishes no explicit license and a 4.9 MB opaque executable is unnecessary for the workflow.

Before replacing `7za.exe` or changing the hashing script, run the hash regression tests and rebuild a release locally.
