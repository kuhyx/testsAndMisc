# Device Owner provisioning: pre-wipe checklist (Pixel 6a, 23181JEGR08034)

Status: **planning only. No wipe has been performed and none is scheduled.**

Device Owner is the only unrooted tier that meets the "cannot be shut down from
the phone" requirement. `dpm set-device-owner` refuses to run while any account
exists on the device, and this phone has six, so provisioning costs a factory
reset. This is what that would take.

## The Google Wallet blocker does not apply to this device

The one genuinely unresolved risk was whether tap-to-pay survives
self-provisioned Device Owner. Research found no mechanism by which DO alone
disables Wallet — the documented failure causes are root, custom ROM, unlocked
bootloader and uncertified devices, none of which DO touches — but also no
first-hand report from anyone who self-provisioned bare DO on a recent Pixel
and then confirmed a successful contactless payment.

**Checked on the device instead of arguing about it:**

```
pm list packages -f com.google.android.apps.walletnfcrel   -> not installed
settings get secure nfc_payment_default_component          -> null
```

Google Wallet is **not installed** and **no NFC payment default is set**. There
is no tap-to-pay to lose. The blocker is moot here; it would only return if you
later start using Wallet, and by then the DO app's release path gives you a
no-wipe exit to test with.

## What is actually on this phone

The earlier checklist was drafted from `phone_focus_mode/config.sh`, which
describes the **rooted** phone. Verified against the Pixel by `pm list packages`,
these are absent: **Aegis, Microsoft Authenticator, Oracle IDM Authenticator,
PKO IKO, Google Wallet.**

Present and relevant:

| App | Package | Survives Google backup? |
|---|---|---|
| KeePassDX | `com.kunzisoft.keepass.libre` | File-based — you own the `.kdbx` |
| Signal | `org.thoughtcrime.securesms` | **No** — needs its own backup |
| mBank | `pl.mbank` | No — device re-pairing |
| Revolut | `com.revolut.revolut` | No — re-login + possible re-verification |
| mObywatel | `pl.nask.mobywatel` | No — full re-activation |

**No dedicated TOTP app is installed**, so the usual "authenticator seeds are
destroyed by the wipe" trap does not apply — unless your TOTP secrets live
inside the KeePassDX database, which is likely. If so, the `.kdbx` file *is*
your seed backup, and step 2 covers it.

## Phase A — break the circular dependency first

Re-verifying a bank typically needs an SMS **and** a second factor; if the
second factor died with the wipe, the loop closes on you. Do these before
touching anything.

1. **Print Google backup codes for both accounts** (`321krzychu@gmail.com`,
   `krzysztofrudnicki0@gmail.com`) — myaccount.google.com → Security → 2-Step
   Verification → Backup codes. If your only second factor is an on-device
   prompt or passkey, the wipe locks you out of the accounts that gate
   everything else.
2. **Copy the KeePassDX database off the device, and its keyfile if you use
   one.** This is the highest-value artifact on the phone.
   ```bash
   adb -s 23181JEGR08034 shell 'find /sdcard -iname "*.kdbx" 2>/dev/null'
   adb -s 23181JEGR08034 pull <path> ~/phone-backup/
   ```
3. **Write down on paper**: mBank customer ID + password, Revolut passcode,
   Signal PIN, KeePassDX master password, both Google passwords.
4. **Confirm the SIM and number will keep working** — nearly every
   re-activation below sends an SMS.

## Phase B — export

5. **Signal**: Settings → Backups → On-device backups. **Record the 30-digit
   passphrase on paper** — it is not your Signal PIN.
   ```bash
   adb -s 23181JEGR08034 pull /sdcard/Signal/Backups/ ~/phone-backup/signal/
   ```
   Registration Lock: forgetting the PIN locks you out for up to 7 days.
6. **Photos and downloads**:
   ```bash
   adb -s 23181JEGR08034 pull /sdcard/DCIM/ ~/phone-backup/DCIM/
   adb -s 23181JEGR08034 pull /sdcard/Download/ ~/phone-backup/Download/
   ```
7. **mBank**: in the transactional service, note how to remove a paired device.
   The old phone stays listed as active after a reset and must be detached.
8. **VERIFY EVERY EXPORT BEFORE WIPING.** Open the `.kdbx` on the PC. An
   untested export is not a backup — this is the step people skip and regret.

## Phase C — wipe and provision, in this order

9. **Factory reset.**
10. **Provision DO immediately, before signing into anything** — the account
    check is what blocks it:
    ```bash
    adb install -r focus_owner/build/app/outputs/flutter-apk/app-debug.apk
    adb shell dpm set-device-owner com.kuhy.focus_owner/.FocusDeviceAdminReceiver
    ```
11. **Test the escape hatch before adding a single account.** Open Focus Owner,
    confirm it reports `Device owner: yes`, press **Release device owner**, and
    confirm it flips back to `no`. Then re-provision. If release does not work,
    stop — a DO app that cannot let go is a soft-brick waiting to happen, and at
    this moment you have nothing to lose by wiping again.
12. **Add one Google account.** Verify banking apps install and log in.
13. **Restore KeePassDX**, then Signal (the restore prompt appears at install
    time only — do not skip past it).
14. **Banks.** mBank: pair via app or transactional service, SMS code, then app
    PIN and mobile authorisation. Revolut: re-login, SMS/email, possible selfie
    re-verification.
15. **mObywatel last.** Re-activation needs Profil Zaufany or a **bank login**
    plus SMS — which is why the banks must work first. Activating on the new
    device automatically deactivates the old one, so there is no rollback.
    Verify current steps at <https://www.gov.pl/web/mobywatel> before relying on
    this.
16. **Only then** apply enforcement, one restriction at a time, re-testing the
    release path after each.

## Do not set these until the rest is proven

`DISALLOW_FACTORY_RESET` and `DISALLOW_DEBUGGING_FEATURES` close your own repair
routes as well as your bypass routes. Combined with an always-on VPN lockdown
they are the specific combination most likely to leave an unrecoverable device.
Add them last, if at all.

## Rollback

`DevicePolicyBridge.releaseDeviceOwner()` (`clearDeviceOwnerApp`) removes DO with
no wipe, but only while the app is installed and working. `dpm
remove-active-admin` does **not** work on a device owner. If the app is
uninstalled without releasing first, the only exit is another factory reset.
