'''
**Opt-in installer for [Nodel WebUI v2](https://github.com/mcartmel/nodel-webui-v2).**

The updater manages the V2 entry pages (`nodes.html`, `nodel.html`,
`toolkit.html`, and `components.html`) and the `v2/` asset tree under
`<hostroot>/custom/content`. It leaves Nodel's bundled V1 interface and
unrelated custom content untouched. The updater also leaves `index.htm` alone
unless **Also install index.htm** is enabled.

###### Safe updates

- Verifies the release source, GitHub artifact attestation, ZIP, and SHA-256
  inventory in `release.json`.
- Uses a recoverable staged swap and keeps the previous managed set for
  **Rollback**. Interrupted swaps are restored when the node starts.
- Reports new releases and local changes through **CheckForUpdates**. Scheduled
  checks never install.

Run **Update** with the installed release tag to replace local changes with the
published release.

_This node can be retired once WebUI v2 ships with Nodel._
'''

import os
import base64
import jarray
from java.io import File, FileInputStream, FileOutputStream, BufferedInputStream, BufferedOutputStream, RandomAccessFile
# handlers catch (Exception, Throwable): Jython's "except Exception" matches only
# Python exceptions, so a Java throwable would otherwise escape every handler here
from java.lang import Throwable
from java.net import URL, URLConnection
from java.nio.file import Files
from java.security import MessageDigest
from java.util.zip import ZipFile
from org.nodel.io import Stream

DEFAULT_REPO = 'mcartmel/nodel-webui-v2'
UA = 'nodel-webui-v2-updater'
ENTRY_PAGES = ['nodes.html', 'nodel.html', 'toolkit.html', 'components.html']
INDEX_PAGE = 'index.htm'
STATE_DIR = '.webui-v2-updater'
GENERATION_FILE = 'generation.json'
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_SHA_BYTES = 4096
MAX_ARCHIVE_ENTRIES = 5000
MAX_ARCHIVE_ENTRY_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_BYTES = 250 * 1024 * 1024

param_repo = Parameter({
    'title': 'GitHub repository (owner/name)',
    'schema': {'type': 'string', 'hint': DEFAULT_REPO},
    'order': 1})

param_pinnedVersion = Parameter({
    'title': 'Pinned version tag (blank = latest stable release)',
    'schema': {'type': 'string', 'hint': 'e.g. v0.1.2'},
    'order': 2})

param_checkIntervalHours = Parameter({
    'title': 'Update check interval (hours, 0 = disabled)',
    'schema': {'type': 'integer'},
    'default': 24,
    'order': 3})

param_installIndexHtm = Parameter({
    'title': 'Also install index.htm (replaces the v1 landing page!)',
    'schema': {'type': 'boolean'},
    'default': False,
    'order': 4})

param_hostRoot = Parameter({
    'title': 'Host root override (blank = auto-detect)',
    'schema': {'type': 'string'},
    'order': 5})

local_event_Status = LocalEvent({
    'group': 'Status', 'order': 9990,
    'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer'},
        'message': {'type': 'string'}}}})

local_event_LastChecked = LocalEvent({
    'group': 'Status', 'schema': {'type': 'string'}})

local_event_InstalledVersion = LocalEvent({
    'group': 'Versions', 'order': 1, 'schema': {'type': 'string'}})

local_event_LatestVersion = LocalEvent({
    'group': 'Versions', 'order': 2, 'schema': {'type': 'string'}})

local_event_UpdateAvailable = LocalEvent({
    'group': 'Versions', 'order': 3, 'schema': {'type': 'boolean'}})

local_event_InstallationIntegrity = LocalEvent({
    'group': 'Versions', 'order': 4,
    'schema': {'type': 'string', 'enum': ['Verified', 'Modified', 'Unknown']}})

_busy = False


# --- filesystem helpers ---

def _host_root():
    if not is_blank(param_hostRoot):
        root = File(param_hostRoot)
    else:
        # node lives at <hostroot>/nodes/<name>
        root = _node.getRoot().getParentFile().getParentFile()

    if not File(root, 'custom/content').isDirectory():
        raise Exception('could not locate host root (no custom/content under "%s"); '
                        'set the Host Root parameter' % root)
    return root

def _paths():
    root = _host_root()
    state = File(root, 'custom/' + STATE_DIR)
    content = File(root, 'custom/content')
    if Files.isSymbolicLink(content.toPath()):
        raise Exception('custom/content must not be a symbolic link')
    if Files.isSymbolicLink(state.toPath()):
        raise Exception('updater state directory must not be a symbolic link')
    return {'content': content,
            'state': state,
            'downloads': File(state, 'downloads'),
            'staging': File(state, 'staging'),
            'backup': File(state, 'backup'),
            'previousBackup': File(state, 'previous-backup'),
            'swap': File(state, 'swap-tmp'),
            'discard': File(state, 'discard-tmp'),
            'transaction': File(state, 'transaction.json'),
            'transactionTemp': File(state, 'transaction.json.tmp'),
            'marker': File(state, 'installed.json'),
            'lock': File(state, 'updater.lock')}

def _page_set():
    pages = list(ENTRY_PAGES)
    if param_installIndexHtm == True:
        pages.append(INDEX_PAGE)
    return pages

def _is_managed_path(path, pages):
    return path in pages or path.startswith('v2/')

def _path_exists(f):
    return f.exists() or Files.isSymbolicLink(f.toPath())

def _is_within(f, root):
    rootPath = root.getCanonicalPath()
    path = f.getCanonicalPath()
    return path == rootPath or path.startswith(rootPath + os.sep)

def _rm_tree(f, allowedRoot=None):
    if not _path_exists(f):
        return
    if allowedRoot is None:
        allowedRoot = _paths()['state']
    if Files.isSymbolicLink(allowedRoot.toPath()):
        raise Exception('refusing cleanup through symbolic-link root "%s"' % allowedRoot)
    parent = f.getParentFile()
    if parent is None or not _is_within(parent, allowedRoot):
        raise Exception('refusing cleanup outside "%s": "%s"' % (allowedRoot, f))
    if Files.isSymbolicLink(f.toPath()):
        if not f.delete():
            raise Exception('could not delete symbolic link "%s"' % f)
        return
    if not _is_within(f, allowedRoot):
        raise Exception('refusing cleanup outside "%s": "%s"' % (allowedRoot, f))
    if f.isDirectory():
        kids = f.listFiles()
        if kids is not None:
            for k in kids:
                _rm_tree(k, allowedRoot)
    if not f.delete():
        raise Exception('could not delete "%s"' % f)

def _move(src, dst):
    if not _path_exists(src):
        raise Exception('could not move missing path "%s"' % src)
    if _path_exists(dst):
        raise Exception('move destination already exists: "%s"' % dst)
    dst.getParentFile().mkdirs()
    if not src.renameTo(dst):
        raise Exception('could not move "%s" to "%s"' % (src, dst))

def _copy_stream(ins, outs, maxBytes=None):
    buf = jarray.zeros(16384, 'b')
    total = 0
    while True:
        n = ins.read(buf)
        if n < 0:
            break
        total += n
        if maxBytes is not None and total > maxBytes:
            raise Exception('stream exceeds %s-byte safety limit' % maxBytes)
        outs.write(buf, 0, n)
    return total

def _write_text(f, text):
    f.getParentFile().mkdirs()
    fh = open(f.getAbsolutePath(), 'wb')
    try:
        fh.write(text)
    finally:
        fh.close()

def _sha256_file(f):
    md = MessageDigest.getInstance('SHA-256')
    ins = BufferedInputStream(FileInputStream(f))
    try:
        buf = jarray.zeros(16384, 'b')
        while True:
            n = ins.read(buf)
            if n < 0:
                break
            md.update(buf, 0, n)
    finally:
        ins.close()
    return ''.join(['%02x' % (b & 0xff) for b in md.digest()])

def _acquire_host_lock():
    p = _paths()
    p['state'].mkdirs()
    if Files.isSymbolicLink(p['lock'].toPath()):
        raise Exception('updater lock must not be a symbolic link')
    channel = RandomAccessFile(p['lock'], 'rw').getChannel()
    try:
        held = channel.tryLock()
    except (Exception, Throwable):
        # tryLock raises OverlappingFileLockException when this JVM already holds
        # the lock, which is the usual case for a second updater node
        held = None
    if held is None:
        channel.close()
        raise Exception('another WebUI v2 updater is active on this host')
    return channel

def _release_host_lock(channel):
    # Closing the channel releases every lock taken through it. FileLock.release()
    # must not be called: its runtime class is sun.nio.ch.FileLockImpl, which
    # java.base does not export, so Jython cannot invoke it on Java 16 or later.
    if channel is not None:
        channel.close()


# --- GitHub access ---

def _repo():
    return param_repo if not is_blank(param_repo) else DEFAULT_REPO

def _api_get(path):
    raw = get_url('https://api.github.com/%s' % path,
                  headers={'User-Agent': UA, 'Accept': 'application/vnd.github+json'},
                  connectTimeout=10, readTimeout=30)
    return json_decode(raw)

def _resolve_release(tag):
    if is_blank(tag):
        return _api_get('repos/%s/releases/latest' % _repo())
    return _api_get('repos/%s/releases/tags/%s' % (_repo(), tag))

def _download(url, destFile, maxBytes):
    # Jython resolves a method against the object's runtime class, and an HTTPS
    # connection is a sun.net.www.protocol.https instance that java.base does not
    # export. Calling through the exported java.net.URLConnection supertype keeps
    # these working on Java 16 and later.
    conn = URL(url).openConnection()
    URLConnection.setConnectTimeout(conn, 15000)
    URLConnection.setReadTimeout(conn, 120000)
    URLConnection.setRequestProperty(conn, 'User-Agent', UA)
    declared = URLConnection.getContentLengthLong(conn)
    if declared > maxBytes:
        raise Exception('download exceeds %s-byte safety limit' % maxBytes)
    # the BufferedInputStream wrapper keeps the later read and close calls on an
    # exported java.io class rather than the connection's internal stream
    ins = BufferedInputStream(URLConnection.getInputStream(conn))
    try:
        destFile.getParentFile().mkdirs()
        outs = BufferedOutputStream(FileOutputStream(destFile))
        try:
            _copy_stream(ins, outs, maxBytes)
        finally:
            outs.close()
    finally:
        ins.close()


# --- verification ---

def _extract_zip(zipPath, destDir):
    destDir.mkdirs()
    destBase = destDir.getCanonicalPath()
    zf = ZipFile(zipPath)
    try:
        entries = zf.entries()
        count = 0
        total = 0
        while entries.hasMoreElements():
            entry = entries.nextElement()
            count += 1
            if count > MAX_ARCHIVE_ENTRIES:
                raise Exception('archive contains more than %s entries' % MAX_ARCHIVE_ENTRIES)
            name = entry.getName()
            # strict: reject anything resembling traversal or absolute paths
            if name.startswith('/') or '..' in name or '\\' in name:
                raise Exception('unsafe path in archive: "%s"' % name)
            target = File(destDir, name)
            if not target.getCanonicalPath().startswith(destBase + os.sep):
                raise Exception('archive path escapes staging: "%s"' % name)
            if entry.isDirectory():
                target.mkdirs()
                continue
            size = entry.getSize()
            if size > MAX_ARCHIVE_ENTRY_BYTES:
                raise Exception('archive entry exceeds safety limit: "%s"' % name)
            if size >= 0 and total + size > MAX_ARCHIVE_BYTES:
                raise Exception('archive exceeds %s-byte expansion limit' % MAX_ARCHIVE_BYTES)
            target.getParentFile().mkdirs()
            ins = zf.getInputStream(entry)
            try:
                outs = BufferedOutputStream(FileOutputStream(target))
                try:
                    written = _copy_stream(ins, outs, MAX_ARCHIVE_ENTRY_BYTES)
                finally:
                    outs.close()
            finally:
                ins.close()
            total += written
            if total > MAX_ARCHIVE_BYTES:
                raise Exception('archive exceeds %s-byte expansion limit' % MAX_ARCHIVE_BYTES)
        return count
    finally:
        zf.close()

def _verify_inventory(stagingDir, release):
    if release.get('inventoryAlgorithm') != 'sha256':
        raise Exception('unsupported inventory algorithm "%s"' % release.get('inventoryAlgorithm'))

    excludes = release.get('inventoryExcludes') or []
    if len(excludes) != 1 or excludes[0] != 'release.json':
        raise Exception('inventoryExcludes must contain only release.json')

    expected = {}
    for entry in release.get('files') or []:
        path = entry.get('path')
        sha256 = entry.get('sha256')
        if path is None or path.startswith('/') or '..' in path or '\\' in path:
            raise Exception('unsafe path in release inventory: "%s"' % path)
        if path in expected:
            raise Exception('duplicate path in release inventory: "%s"' % path)
        if sha256 is None or len(sha256) != 64:
            raise Exception('invalid SHA-256 for "%s"' % path)
        expected[path] = sha256.lower()
    if len(expected) == 0:
        raise Exception('release.json contains no file inventory')

    for path in expected.keys():
        f = File(stagingDir, path)
        if not f.isFile():
            raise Exception('inventory file missing from archive: "%s"' % path)
        actual = _sha256_file(f)
        if actual != expected[path]:
            raise Exception('hash mismatch for "%s"' % path)

    base = stagingDir.getAbsolutePath()
    unexpected = []
    for dirpath, dirnames, filenames in os.walk(base):
        for name in filenames:
            rel = os.path.join(dirpath, name)[len(base) + 1:].replace('\\', '/')
            if rel not in expected and rel not in excludes:
                unexpected.append(rel)
    if len(unexpected) > 0:
        raise Exception('unexpected files in archive: %s' % ', '.join(unexpected[:5]))

    return len(expected)

def _managed_inventory(stagingDir, release):
    pages = _page_set()
    expected = {}
    for entry in release.get('files') or []:
        expected[entry.get('path')] = entry.get('sha256')

    for page in pages:
        if page not in expected or not File(stagingDir, page).isFile():
            raise Exception('release is missing required managed page "%s"' % page)

    stagedV2 = File(stagingDir, 'v2')
    if not stagedV2.isDirectory() or Files.isSymbolicLink(stagedV2.toPath()):
        raise Exception('release is missing the required v2 asset directory')

    managed = []
    for path in sorted(expected.keys()):
        if path is not None and _is_managed_path(path, pages):
            managed.append({'path': path, 'sha256': expected[path]})

    v2Files = 0
    base = stagingDir.getAbsolutePath()
    for dirpath, dirnames, filenames in os.walk(stagedV2.getAbsolutePath()):
        for name in filenames:
            path = os.path.join(dirpath, name)[len(base) + 1:].replace('\\', '/')
            if path not in expected:
                raise Exception('managed asset is not covered by inventory: "%s"' % path)
            v2Files += 1
    if v2Files == 0:
        raise Exception('release contains no v2 assets')
    return managed

def _verify_release_contract(release, tag):
    source = release.get('source') or {}
    if (source.get('repository') or '').lower() != _repo().lower():
        raise Exception('release.json repository does not match configured repository')
    if source.get('tag') != tag:
        raise Exception('release.json tag "%s" does not match release tag "%s"'
                        % (source.get('tag'), tag))
    if source.get('dirty') != False or source.get('publishable') != True:
        raise Exception('release.json does not describe a clean, publishable build')

    commit = release.get('commit')
    if (commit is None or len(commit) != 40 or
            not all([c in '0123456789abcdef' for c in commit.lower()])):
        raise Exception('release.json contains no valid source commit')
    resolved = _api_get('repos/%s/commits/%s' % (_repo(), tag)).get('sha')
    if resolved != commit:
        raise Exception('release.json commit does not match the configured repository tag')

def _verify_attestation(assetName, digest, release, tag):
    result = _api_get('repos/%s/attestations/sha256:%s' % (_repo(), digest))
    expectedRepo = 'https://github.com/%s' % _repo().lower()
    expectedRef = 'refs/tags/%s' % tag
    expectedCommit = release.get('commit')

    for attestation in result.get('attestations') or []:
        try:
            envelope = (attestation.get('bundle') or {}).get('dsseEnvelope') or {}
            statement = json_decode(base64.b64decode(envelope.get('payload')))
            if statement.get('predicateType') != 'https://slsa.dev/provenance/v1':
                continue

            subjectMatches = False
            for subject in statement.get('subject') or []:
                if (subject.get('name') == assetName and
                        (subject.get('digest') or {}).get('sha256') == digest):
                    subjectMatches = True
                    break
            if not subjectMatches:
                continue

            predicate = statement.get('predicate') or {}
            definition = predicate.get('buildDefinition') or {}
            workflow = (definition.get('externalParameters') or {}).get('workflow') or {}
            if (workflow.get('repository') or '').lower() != expectedRepo:
                continue
            if workflow.get('ref') != expectedRef:
                continue

            commitMatches = False
            for dependency in definition.get('resolvedDependencies') or []:
                if (dependency.get('digest') or {}).get('gitCommit') == expectedCommit:
                    commitMatches = True
                    break
            if commitMatches:
                return
        except (Exception, Throwable):
            pass

    raise Exception('ZIP has no matching GitHub artifact attestation')

def _integrity_problems(info):
    if info is None or not info.get('managedFiles'):
        return None

    expected = {}
    for entry in info.get('managedFiles'):
        path = entry.get('path')
        sha256 = entry.get('sha256')
        if path is None or sha256 is None:
            return None
        expected[path] = sha256

    content = _paths()['content']
    problems = []
    for path in sorted(expected.keys()):
        live = File(content, path)
        if Files.isSymbolicLink(live.toPath()):
            problems.append('symbolic link %s' % path)
        elif not live.isFile():
            problems.append('missing %s' % path)
        elif _sha256_file(live) != expected[path]:
            problems.append('modified %s' % path)

    v2 = File(content, 'v2')
    if Files.isSymbolicLink(v2.toPath()):
        problems.append('symbolic link v2')
    elif v2.isDirectory():
        base = content.getAbsolutePath()
        for dirpath, dirnames, filenames in os.walk(v2.getAbsolutePath()):
            for name in filenames:
                path = os.path.join(dirpath, name)[len(base) + 1:].replace('\\', '/')
                if path not in expected:
                    problems.append('unexpected %s' % path)

    return sorted(problems)


# --- install / rollback ---

def _installed_info():
    p = _paths()
    if Files.isSymbolicLink(p['marker'].toPath()):
        console.warn('installed marker must not be a symbolic link')
        return None
    if not p['marker'].isFile():
        return None
    try:
        return json_decode(Stream.readFully(p['marker']))
    except (Exception, Throwable), e:
        console.warn('could not read installed marker: %s' % e)
        return None

def _marker_info(marker):
    if Files.isSymbolicLink(marker.toPath()):
        raise Exception('installed marker must not be a symbolic link')
    if not marker.isFile():
        return None
    return json_decode(Stream.readFully(marker))

def _same_release(info, tag):
    return (info is not None and info.get('tag') == tag and
            (info.get('repo') or '').lower() == _repo().lower())

def _manages_index(info, fallback=False):
    if info is None:
        return False
    managed = info.get('managedFiles')
    if managed is None:
        return fallback
    for entry in managed:
        if entry.get('path') == INDEX_PAGE:
            return True
    return False

def _emit_installed():
    info = _installed_info()
    if info is not None:
        local_event_InstalledVersion.emitIfDifferent(info.get('tag') or 'unknown')
    elif File(_paths()['content'], 'v2').isDirectory():
        local_event_InstalledVersion.emitIfDifferent('unmanaged')
    else:
        local_event_InstalledVersion.emitIfDifferent('not installed')

def _emit_integrity():
    problems = _integrity_problems(_installed_info())
    if problems is None:
        local_event_InstallationIntegrity.emitIfDifferent('Unknown')
    elif len(problems) > 0:
        local_event_InstallationIntegrity.emitIfDifferent('Modified')
    else:
        local_event_InstallationIntegrity.emitIfDifferent('Verified')
    return problems

def _write_transaction(info):
    p = _paths()
    if _path_exists(p['transaction']):
        raise Exception('an updater transaction is already in progress')
    if _path_exists(p['transactionTemp']):
        _rm_tree(p['transactionTemp'])
    _write_text(p['transactionTemp'], json_encode(info))
    syncFile = RandomAccessFile(p['transactionTemp'], 'rw')
    try:
        syncFile.getFD().sync()
    finally:
        syncFile.close()
    _move(p['transactionTemp'], p['transaction'])

def _finish_transaction():
    transaction = _paths()['transaction']
    if _path_exists(transaction) and not transaction.delete():
        raise Exception('could not remove completed transaction marker')

def _cleanup_committed_state(p):
    if _path_exists(p['discard']):
        _rm_tree(p['discard'])
    if p['previousBackup'].isDirectory():
        _move(p['previousBackup'], p['discard'])
        _rm_tree(p['discard'])

def _live_matches_activation(info):
    marker = _installed_info()
    if info.get('activationHasMarker') == True:
        return (marker is not None and marker.get('tag') == info.get('activationTag') and
                (marker.get('repo') or '').lower() == (info.get('activationRepo') or '').lower())
    return not _path_exists(_paths()['marker'])

def _recover_transaction():
    p = _paths()
    if Files.isSymbolicLink(p['transaction'].toPath()):
        raise Exception('transaction marker must not be a symbolic link')
    if not p['transaction'].isFile():
        if _path_exists(p['transactionTemp']):
            _rm_tree(p['transactionTemp'])
        _cleanup_committed_state(p)
        return False
    try:
        info = json_decode(Stream.readFully(p['transaction']))
    except (Exception, Throwable), e:
        raise Exception('transaction marker is unreadable; preserve updater state for recovery: %s' % e)

    operation = info.get('operation')
    if operation not in ['install', 'rollback']:
        raise Exception('unknown updater transaction; preserve updater state for recovery')

    snapshot = p['swap'] if p['swap'].isDirectory() else None
    if snapshot is None:
        if not _live_matches_activation(info):
            _finish_transaction()
            return True
        if info.get('preserveBackup') == True:
            _finish_transaction()
            try:
                _cleanup_committed_state(p)
            except (Exception, Throwable), e:
                console.warn('repaired installation recovered; old swap cleanup failed: %s' % e)
            return True
        if not p['backup'].isDirectory():
            raise Exception('committed transaction has no recovery snapshot')
        snapshot = p['backup']

    if operation == 'rollback':
        if p['previousBackup'].isDirectory() or snapshot == p['backup']:
            backupStore = p['previousBackup']
            backupStore.mkdirs()
        else:
            backupStore = p['backup']
            backupStore.mkdirs()

        for name in info.get('backupNames') or []:
            stored = File(backupStore, name)
            if not _path_exists(stored):
                live = File(p['content'], name)
                if not _path_exists(live):
                    raise Exception('cannot recover missing rollback item "%s"' % name)
                _move(live, stored)
        if info.get('backupHasMarker') == True:
            storedMarker = File(backupStore, 'installed.json')
            if not storedMarker.isFile():
                if not p['marker'].isFile():
                    raise Exception('cannot recover missing rollback marker')
                _move(p['marker'], storedMarker)

    originalNames = info.get('originalNames') or []
    targetNames = info.get('targetNames') or []
    for name in targetNames:
        saved = File(snapshot, name)
        live = File(p['content'], name)
        if _path_exists(saved):
            if _path_exists(live):
                _rm_tree(live, p['content'])
            _move(saved, live)
        elif name not in originalNames and _path_exists(live):
            _rm_tree(live, p['content'])

    savedMarker = File(snapshot, 'installed.json')
    if savedMarker.isFile():
        if p['marker'].isFile() and not p['marker'].delete():
            raise Exception('could not remove partial installed marker')
        _move(savedMarker, p['marker'])
    elif info.get('originalHasMarker') != True and p['marker'].isFile():
        if not p['marker'].delete():
            raise Exception('could not remove partial installed marker')

    if snapshot == p['backup']:
        _rm_tree(p['backup'])
    elif p['swap'].isDirectory():
        _rm_tree(p['swap'])

    if p['previousBackup'].isDirectory():
        if p['backup'].isDirectory():
            _rm_tree(p['backup'])
        _move(p['previousBackup'], p['backup'])

    _finish_transaction()
    console.warn('recovered an interrupted WebUI v2 updater transaction')
    return True

def _capture_current(p, targetNames):
    originalNames = []
    for name in targetNames:
        if _path_exists(File(p['content'], name)):
            originalNames.append(name)
    return originalNames

def _install_staged(stagingDir, release, tag, preserveBackup=False):
    p = _paths()
    if Files.isSymbolicLink(p['marker'].toPath()):
        raise Exception('installed marker must not be a symbolic link')
    pages = _page_set()
    targetNames = ['v2'] + pages
    managedFiles = _managed_inventory(stagingDir, release)
    markerText = json_encode({
        'tag': tag,
        'version': release.get('version'),
        'commit': release.get('commit'),
        'repo': _repo(),
        'installedAt': str(date_now()),
        'installIndexHtm': param_installIndexHtm == True,
        'managedFiles': managedFiles})

    if _path_exists(p['swap']) or _path_exists(p['previousBackup']):
        raise Exception('orphaned updater swap state requires inspection before installing')

    originalNames = _capture_current(p, targetNames)
    _write_transaction({
        'operation': 'install',
        'targetNames': targetNames,
        'originalNames': originalNames,
        'originalHasMarker': p['marker'].isFile(),
        'activationHasMarker': True,
        'activationTag': tag,
        'activationRepo': _repo(),
        'preserveBackup': preserveBackup})
    p['swap'].mkdirs()
    _write_text(File(p['swap'], GENERATION_FILE), json_encode({
        'names': originalNames,
        'hasMarker': p['marker'].isFile()}))

    try:
        for name in originalNames:
            _move(File(p['content'], name), File(p['swap'], name))
        if p['marker'].isFile():
            _move(p['marker'], File(p['swap'], 'installed.json'))

        for name in targetNames:
            _move(File(stagingDir, name), File(p['content'], name))
        _write_text(p['marker'], markerText)

        if preserveBackup:
            _move(p['swap'], p['discard'])
            _finish_transaction()
            try:
                _cleanup_committed_state(p)
            except (Exception, Throwable), e:
                console.warn('repair completed but old swap cleanup failed: %s' % e)
        else:
            if p['backup'].isDirectory():
                _move(p['backup'], p['previousBackup'])
            _move(p['swap'], p['backup'])
            _finish_transaction()
            try:
                _cleanup_committed_state(p)
            except (Exception, Throwable), e:
                console.warn('install completed but old backup cleanup failed: %s' % e)
    except (Exception, Throwable):
        _recover_transaction()
        raise


# --- actions ---

@local_action({'group': 'Updater', 'order': 1})
def CheckForUpdates(arg=None):
    _do_check()

def _do_check():
    if _busy:
        console.warn('busy - ignoring check request')
        return
    hostLock = None
    try:
        hostLock = _acquire_host_lock()
        _recover_transaction()
        local_event_LastChecked.emit(str(date_now()))
        _emit_installed()
        problems = _emit_integrity()

        release = _resolve_release(param_pinnedVersion)
        latestTag = release.get('tag_name')
        local_event_LatestVersion.emitIfDifferent(latestTag)

        installedInfo = _installed_info()
        installed = local_event_InstalledVersion.getArg()
        available = not _same_release(installedInfo, latestTag)
        local_event_UpdateAvailable.emitIfDifferent(available)

        if available:
            suffix = ''
            if problems is not None and len(problems) > 0:
                suffix = '; local changes also detected'
            console.info('update available: installed=%s, latest=%s%s (use the Update action to install)'
                         % (installed, latestTag, suffix))
            local_event_Status.emit({'level': 1, 'message': 'Update available: %s (installed: %s%s)'
                                     % (latestTag, installed, suffix)})
        elif problems is None:
            console.warn('installed-file integrity is unknown for %s; reinstall to establish a baseline'
                         % installed)
            local_event_Status.emit({'level': 1,
                                     'message': 'Up to date (%s); integrity unknown, reinstall to establish baseline'
                                                % latestTag})
        elif len(problems) > 0:
            detail = ', '.join(problems[:3])
            if len(problems) > 3:
                detail += ', and %s more' % (len(problems) - 3)
            console.warn('local changes detected from %s: %s (use Update to restore)'
                         % (installed, detail))
            local_event_Status.emit({'level': 1,
                                     'message': 'Locally modified from %s (%s file%s); use Update to restore'
                                                % (installed, len(problems),
                                                   '' if len(problems) == 1 else 's')})
        else:
            console.info('up to date and verified (%s)' % latestTag)
            local_event_Status.emit({'level': 0, 'message': 'Up to date and verified (%s)' % latestTag})

    except (Exception, Throwable), e:
        console.error('check failed: %s' % e)
        local_event_Status.emit({'level': 2, 'message': 'Check failed: %s' % e})
    finally:
        _release_host_lock(hostLock)

@local_action({'group': 'Updater', 'order': 2,
               'schema': {'type': 'string', 'title': 'Version tag (blank = pinned/latest)'}})
def Update(arg=None):
    global _busy
    if _busy:
        console.warn('busy - ignoring update request')
        return
    _busy = True
    hostLock = None
    try:
        hostLock = _acquire_host_lock()
        _recover_transaction()
        tag = arg if not is_blank(arg) else param_pinnedVersion

        console.info('resolving release (%s)...' % (tag if not is_blank(tag) else 'latest stable'))
        ghRelease = _resolve_release(tag)
        tag = ghRelease.get('tag_name')
        if is_blank(tag) or ghRelease.get('draft') == True:
            raise Exception('GitHub did not return a published release tag')

        installedInfo = _installed_info()
        installedProblems = _integrity_problems(installedInfo)
        sameRelease = _same_release(installedInfo, tag)
        if (installedInfo is not None and installedInfo.get('managedFiles') is not None and
                _manages_index(installedInfo) != (param_installIndexHtm == True)):
            raise Exception('Also install index.htm changed; Rollback before changing this policy')
        if sameRelease and installedProblems is not None and len(installedProblems) == 0:
            local_event_LatestVersion.emitIfDifferent(tag)
            local_event_UpdateAvailable.emitIfDifferent(False)
            local_event_InstallationIntegrity.emitIfDifferent('Verified')
            console.info('%s is already installed and verified; no changes made' % tag)
            local_event_Status.emit({'level': 0, 'message': 'Already installed and verified (%s)' % tag})
            return
        if sameRelease:
            console.warn('%s is already installed - reinstalling (verified repair)' % tag)

        zipAsset, shaAsset = None, None
        for asset in ghRelease.get('assets') or []:
            name = asset.get('name') or ''
            if '/' in name or '\\' in name or name in ['.', '..']:
                raise Exception('release contains an unsafe asset name')
            if name.endswith('.zip.sha256'):
                if shaAsset is not None:
                    raise Exception('release contains more than one ZIP checksum asset')
                shaAsset = asset
            elif name.endswith('.zip'):
                if zipAsset is not None:
                    raise Exception('release contains more than one ZIP asset')
                zipAsset = asset
        if zipAsset is None or shaAsset is None:
            raise Exception('release %s is missing the .zip or .zip.sha256 asset' % tag)
        if zipAsset.get('size') is None or zipAsset.get('size') <= 0 or zipAsset.get('size') > MAX_ZIP_BYTES:
            raise Exception('release ZIP size is outside the updater safety limit')
        if shaAsset.get('size') is None or shaAsset.get('size') <= 0 or shaAsset.get('size') > MAX_SHA_BYTES:
            raise Exception('release checksum size is outside the updater safety limit')

        p = _paths()
        _rm_tree(p['downloads'])
        _rm_tree(p['staging'])

        console.info('downloading %s (%s bytes)...' % (zipAsset['name'], zipAsset['size']))
        zipFile = File(p['downloads'], zipAsset['name'])
        _download(zipAsset['browser_download_url'], zipFile, MAX_ZIP_BYTES)
        shaFile = File(p['downloads'], shaAsset['name'])
        _download(shaAsset['browser_download_url'], shaFile, MAX_SHA_BYTES)

        if zipFile.length() != zipAsset['size']:
            raise Exception('download size mismatch (%s != %s)' % (zipFile.length(), zipAsset['size']))
        if shaFile.length() != shaAsset['size']:
            raise Exception('checksum download size mismatch (%s != %s)'
                            % (shaFile.length(), shaAsset['size']))
        expectedSha = Stream.readFully(shaFile).split()[0].strip().lower()
        if len(expectedSha) != 64 or not all([c in '0123456789abcdef' for c in expectedSha]):
            raise Exception('release checksum is not a valid SHA-256 value')
        actualSha = _sha256_file(zipFile)
        if actualSha != expectedSha:
            raise Exception('ZIP checksum mismatch (expected %s, got %s)' % (expectedSha, actualSha))
        console.info('ZIP checksum verified (%s)' % actualSha[:16])

        fileCount = _extract_zip(zipFile, p['staging'])
        console.info('extracted %s files to staging' % fileCount)

        releaseJsonFile = File(p['staging'], 'release.json')
        if not releaseJsonFile.isFile():
            raise Exception('archive has no release.json')
        release = json_decode(Stream.readFully(releaseJsonFile))
        _verify_release_contract(release, tag)
        _verify_attestation(zipAsset['name'], actualSha, release, tag)
        console.info('GitHub artifact attestation verified for %s' % tag)

        verified = _verify_inventory(p['staging'], release)
        console.info('per-file inventory verified (%s files)' % verified)

        api = release.get('nodelApi')
        if api is not None:
            console.info('release declares Nodel API compatibility: min %s, below %s'
                         % (api.get('min'), api.get('maxExclusive')))

        _install_staged(p['staging'], release, tag, sameRelease)

        cleanupWarning = None
        try:
            _rm_tree(p['staging'])
            _rm_tree(p['downloads'])
        except (Exception, Throwable), e:
            cleanupWarning = str(e)
            console.warn('installed %s but temporary-file cleanup failed: %s' % (tag, e))

        try:
            _emit_installed()
            _emit_integrity()
            latest = local_event_LatestVersion.getArg()
            current = _installed_info()
            local_event_UpdateAvailable.emitIfDifferent(
                latest is not None and not _same_release(current, latest))
        except (Exception, Throwable), e:
            console.warn('installed %s but status refresh failed: %s' % (tag, e))
        console.info('installed %s (previous version retained for Rollback)' % tag)
        if cleanupWarning is None:
            local_event_Status.emit({'level': 0, 'message': 'Installed and verified %s' % tag})
        else:
            local_event_Status.emit({'level': 1,
                                     'message': 'Installed and verified %s; temporary cleanup needs attention'
                                                % tag})

    except (Exception, Throwable), e:
        console.error('update failed: %s' % e)
        local_event_Status.emit({'level': 2, 'message': 'Update failed: %s' % e})
    finally:
        _release_host_lock(hostLock)
        _busy = False

def _rollback_managed_set(p):
    currentInfo = _installed_info()
    backupInfo = _marker_info(File(p['backup'], 'installed.json'))
    names = ['v2'] + ENTRY_PAGES
    currentOwnsIndex = _manages_index(currentInfo, param_installIndexHtm == True)
    backupOwnsIndex = (_manages_index(backupInfo, False) or
                       File(p['backup'], INDEX_PAGE).exists())
    if currentOwnsIndex or backupOwnsIndex:
        names.append(INDEX_PAGE)
    return names

def _rollback(p):
    if Files.isSymbolicLink(p['marker'].toPath()):
        raise Exception('installed marker must not be a symbolic link')
    targetNames = _rollback_managed_set(p)
    backupNames = []
    backupHasMarker = False
    for backedUp in p['backup'].listFiles() or []:
        name = backedUp.getName()
        if name == 'installed.json':
            backupHasMarker = True
        elif name == GENERATION_FILE:
            pass
        elif name in targetNames:
            backupNames.append(name)
        else:
            raise Exception('backup contains unexpected item "%s"' % name)

    if _path_exists(p['swap']) or _path_exists(p['previousBackup']):
        raise Exception('orphaned updater swap state requires inspection before rollback')

    originalNames = _capture_current(p, targetNames)
    backupInfo = _marker_info(File(p['backup'], 'installed.json'))
    _write_transaction({
        'operation': 'rollback',
        'targetNames': targetNames,
        'originalNames': originalNames,
        'originalHasMarker': p['marker'].isFile(),
        'backupNames': backupNames,
        'backupHasMarker': backupHasMarker,
        'activationHasMarker': backupHasMarker,
        'activationTag': backupInfo.get('tag') if backupInfo is not None else None,
        'activationRepo': backupInfo.get('repo') if backupInfo is not None else None})
    p['swap'].mkdirs()
    _write_text(File(p['swap'], GENERATION_FILE), json_encode({
        'names': originalNames,
        'hasMarker': p['marker'].isFile()}))

    try:
        for name in originalNames:
            _move(File(p['content'], name), File(p['swap'], name))
        if p['marker'].isFile():
            _move(p['marker'], File(p['swap'], 'installed.json'))

        for name in backupNames:
            _move(File(p['backup'], name), File(p['content'], name))
        if backupHasMarker:
            _move(File(p['backup'], 'installed.json'), p['marker'])

        _move(p['backup'], p['previousBackup'])
        _move(p['swap'], p['backup'])
        _finish_transaction()
        try:
            _cleanup_committed_state(p)
        except (Exception, Throwable), e:
            console.warn('rollback completed but old backup cleanup failed: %s' % e)
    except (Exception, Throwable):
        _recover_transaction()
        raise

@local_action({'group': 'Updater', 'order': 3})
def Rollback(arg=None):
    global _busy
    if _busy:
        console.warn('busy - ignoring rollback request')
        return
    _busy = True
    hostLock = None
    try:
        hostLock = _acquire_host_lock()
        _recover_transaction()
        p = _paths()
        backupKids = p['backup'].listFiles() if p['backup'].isDirectory() else None
        if backupKids is None or len(backupKids) == 0:
            console.warn('no backup available to roll back to')
            local_event_Status.emit({'level': 1, 'message': 'No backup available'})
            return

        _rollback(p)

        _emit_installed()
        _emit_integrity()
        latest = local_event_LatestVersion.getArg()
        restored = _installed_info()
        local_event_UpdateAvailable.emitIfDifferent(
            latest is not None and not _same_release(restored, latest))
        console.info('rolled back; previous set retained (Rollback again to undo)')
        local_event_Status.emit({'level': 0, 'message': 'Rolled back to %s'
                                 % local_event_InstalledVersion.getArg()})

    except (Exception, Throwable), e:
        console.error('rollback failed: %s' % e)
        local_event_Status.emit({'level': 2, 'message': 'Rollback failed: %s' % e})
    finally:
        _release_host_lock(hostLock)
        _busy = False


# --- lifecycle ---

_checkTimer = Timer(_do_check, 24 * 3600, stopped=True)

def main():
    console.info('WebUI v2 Updater starting')

@after_main
def setup():
    hostLock = None
    try:
        hostLock = _acquire_host_lock()
        _recover_transaction()
        _emit_installed()
        _emit_integrity()
    except (Exception, Throwable), e:
        console.warn('could not determine installed version: %s' % e)
        local_event_Status.emit({'level': 2, 'message': 'Updater recovery failed: %s' % e})
    finally:
        _release_host_lock(hostLock)

    hours = param_checkIntervalHours if param_checkIntervalHours is not None else 24
    if hours > 0:
        _checkTimer.setDelayAndInterval(60, hours * 3600)
        _checkTimer.start()
        console.info('update checks every %s hour(s) (notify only, never auto-installs)' % hours)
    else:
        console.info('scheduled update checks disabled')
