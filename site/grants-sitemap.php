<?php
/** XML sitemap of the pages Google should index: open opportunities, recently closed ones (120 days),
 *  category pages, collections (grants.php?c=…) and weekly archives (grants.php?week=…). */
require __DIR__ . '/funding-lib.php';
header('Content-Type: application/xml; charset=UTF-8');

$updated = sb_feed()['updated'] ?? date('Y-m-d');
$items = sb_open_items();
$urls = [[SB_BASE_URL . 'grants.php', $updated], [SB_BASE_URL . 'resources.html', $updated]];

foreach ($items as $it) {
    $urls[] = [sb_grant_url($it), $updated];
}
// Recently closed pages stay indexed for 120 days (see grant.php)
$openSlugs = array_column($items, 'slug');
foreach (sb_feed()['items'] as $it) {
    if (in_array($it['slug'], $openSlugs, true) || empty($it['deadline'])) continue;
    if (strtotime($it['deadline']) >= strtotime('-120 days')) $urls[] = [sb_grant_url($it), $it['deadline']];
}

// Category pages with at least 3 open items
$count = [];
foreach ($items as $it) {
    $count['type=' . rawurlencode($it['type'])] = ($count['type=' . rawurlencode($it['type'])] ?? 0) + 1;
    $count['region=' . rawurlencode($it['geography'] ?? 'India')] = ($count['region=' . rawurlencode($it['geography'] ?? 'India')] ?? 0) + 1;
    foreach (sb_list($it['stages'] ?? '') as $s) $count['stage=' . rawurlencode($s)] = ($count['stage=' . rawurlencode($s)] ?? 0) + 1;
    foreach (array_diff(sb_list($it['sectors'] ?? ''), ['All sectors']) as $s) $count['sector=' . rawurlencode($s)] = ($count['sector=' . rawurlencode($s)] ?? 0) + 1;
}
foreach ($count as $q => $n) if ($n >= 3) $urls[] = [SB_BASE_URL . 'grants.php?' . $q, $updated];

// Collections and weekly archives from roundups.json (cached 1 hour)
$cache = sys_get_temp_dir() . '/fundguy_roundups.json';
if (!is_file($cache) || filemtime($cache) < time() - 3600) {
    $raw = @file_get_contents('https://raw.githubusercontent.com/scalerbee/funding-feed/main/roundups.json');
    if ($raw && json_decode($raw, true)) @file_put_contents($cache, $raw);
}
if (is_file($cache)) {
    $rj = json_decode(file_get_contents($cache), true) ?: [];
    foreach ($rj['roundups'] ?? [] as $r) if ($r['count'] >= 3) $urls[] = [SB_BASE_URL . 'grants.php?c=' . rawurlencode($r['slug']), $updated];
    foreach ($rj['weekly'] ?? [] as $w) if ($w['count'] >= 3) $urls[] = [SB_BASE_URL . 'grants.php?week=' . rawurlencode($w['slug']), min($updated, $w['to'])];
}

echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
foreach ($urls as [$loc, $mod]) {
    echo '  <url><loc>' . htmlspecialchars($loc, ENT_XML1 | ENT_QUOTES, 'UTF-8') . '</loc><lastmod>' . h($mod) . "</lastmod></url>\n";
}
echo '</urlset>' . "\n";
