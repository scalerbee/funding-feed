<?php
/** Hub + category pages: grants.php, grants.php?type=Grant, ?stage=MVP, ?sector=DeepTech, ?region=Karnataka
 *  Collections from roundups.json: grants.php?c=closing-soon, ?c=women-founders, ?c=state-karnataka …
 *  Weekly archive: grants.php?week=week-2026-w47 */
require __DIR__ . '/funding-lib.php';

/** roundups.json from the GitHub feed repo, cached for 1 hour (same pattern as the main feed). */
function fg_roundups() {
    static $r = null;
    if ($r !== null) return $r;
    $cache = sys_get_temp_dir() . '/fundguy_roundups.json';
    if (!is_file($cache) || filemtime($cache) < time() - 3600) {
        $raw = @file_get_contents('https://raw.githubusercontent.com/scalerbee/funding-feed/main/roundups.json');
        if ($raw && json_decode($raw, true)) @file_put_contents($cache, $raw);
    }
    $r = is_file($cache) ? (json_decode(file_get_contents($cache), true) ?: []) : [];
    $r += ['roundups' => [], 'weekly' => []];
    return $r;
}

$filters = ['type' => 'Type', 'stage' => 'Stage', 'sector' => 'Sector', 'region' => 'Location'];
$key = null; $val = null; $coll = null;

$all = sb_open_items();
$bySlug = [];
foreach (sb_feed()['items'] as $x) $bySlug[$x['slug']] = $x;

// 1) Collections (?c=) and weekly archive pages (?week=)
if (!empty($_GET['c']) || !empty($_GET['week'])) {
    $want = preg_replace('/[^a-z0-9-]/', '', strtolower((string)($_GET['c'] ?? $_GET['week'])));
    $list = !empty($_GET['c']) ? fg_roundups()['roundups'] : fg_roundups()['weekly'];
    foreach ($list as $r) if ($r['slug'] === $want) { $coll = $r; break; }
    $key = !empty($_GET['c']) ? 'c' : 'week';
    $val = $want;
}
// 2) Simple filters
if (!$key) {
    foreach ($filters as $k => $_) {
        if (!empty($_GET[$k])) { $key = $k; $val = trim(substr((string)$_GET[$k], 0, 60)); break; }
    }
}

$match = function ($it) use ($key, $val) {
    if (!$key) return true;
    $v = strtolower($val);
    switch ($key) {
        case 'type':   return strtolower($it['type'] ?? '') === $v;
        case 'stage':  return in_array($v, array_map('strtolower', sb_list($it['stages'] ?? '')), true);
        case 'sector': return in_array($v, array_map('strtolower', sb_list($it['sectors'] ?? '')), true);
        case 'region': $g = strtolower($it['geography'] ?? 'india');
                       return $g === $v || ($v !== 'india' && $v !== 'global' && $g === 'india');
    }
    return true;
};

$month = date('F Y');
if ($key === 'c' || $key === 'week') {
    if (!$coll) {
        http_response_code(404);
        sb_head('Page not found — Scaler Bee', 'This collection is not available.', SB_BASE_URL . 'grants.php', true);
        echo '<div class="gp-wrap"><div class="gp-card"><h1 class="gp-title">This list is not available</h1>'
           . '<div class="gp-actions"><a class="gp-btn" href="grants.php">Browse open grants</a></div></div></div>';
        sb_foot();
        exit;
    }
    $items = [];
    foreach ($coll['ids'] as $id) {
        if (!isset($bySlug[$id])) continue;
        if ($key === 'c' && !sb_is_open($bySlug[$id])) continue;   // collections show only what's open today
        $items[] = $bySlug[$id];
    }
    $h1   = $key === 'c' ? $coll['title'] . ' — ' . $month : $coll['title'];
    $lede = $coll['intro'];
} else {
    $items = array_values(array_filter($all, $match));
    if (!$key) {
        $h1 = "Open startup grants & funding programmes in India — $month";
        $lede = 'Every grant, challenge, accelerator and government scheme on this page is open for applications right now. Each one is checked against the official source, with deadlines, amounts and eligibility in one place.';
    } else {
        $map = [
            'type'   => ["Open {$val} opportunities for Indian startups — $month", "All {$val} opportunities currently accepting applications from Indian founders, with deadlines, amounts and eligibility."],
            'stage'  => ["Funding for {$val}-stage startups in India — $month", "Grants, challenges and programmes open right now for startups at the {$val} stage."],
            'sector' => ["{$val} startup grants & funding in India — $month", "Open funding opportunities for {$val} startups in India, with deadlines and eligibility."],
            'region' => [($val === 'India' ? "National startup grants open to all of India — $month" : ($val === 'Global' ? "Global startup programmes open to Indian founders — $month" : "Startup grants in {$val} — $month")),
                         ($val === 'Global' ? 'International programmes that accept applications from Indian startups.' : "Programmes open to startups in {$val}, including national schemes any Indian startup can apply to.")],
        ];
        [$h1, $lede] = $map[$key];
    }
}

$canonical = SB_BASE_URL . 'grants.php' . ($key ? '?' . $key . '=' . rawurlencode($val) : '');
$noindex = $key && count($items) < 3; // keep thin pages out of Google
$desc = $lede . ' ' . count($items) . ($key === 'week' ? ' opportunities' : ' open opportunities') . ', updated ' . sb_fmt_date(sb_feed()['updated'] ?? '') . '.';
if (strlen($desc) > 300) $desc = substr($desc, 0, 297) . '…';

$ld = [['@context' => 'https://schema.org', '@type' => 'CollectionPage', 'name' => $h1, 'description' => $lede, 'url' => $canonical,
    'dateModified' => sb_feed()['updated'] ?? date('Y-m-d'), 'author' => sb_person_ld(), 'publisher' => sb_org_ld(),
    'mainEntity' => ['@type' => 'ItemList', 'numberOfItems' => count($items), 'itemListElement' => array_map(function ($it, $i) {
        return ['@type' => 'ListItem', 'position' => $i + 1, 'url' => sb_grant_url($it), 'name' => $it['title']];
    }, $items, array_keys($items))]]];

sb_head($h1 . ' | Scaler Bee', $desc, $canonical, $noindex, $ld);

// Chips for browsing
$types = []; $stagesAll = []; $regions = [];
foreach ($all as $it) {
    $types[$it['type']] = true;
    foreach (sb_list($it['stages'] ?? '') as $s) $stagesAll[$s] = true;
    $regions[$it['geography'] ?? 'India'] = true;
}
$chip = function ($k, $v, $label = null) use ($key, $val) {
    $on = ($key === $k && strcasecmp($val, $v) === 0) ? ' class="on"' : '';
    return '<a' . $on . ' href="grants.php?' . $k . '=' . h(rawurlencode($v)) . '">' . h($label ?? $v) . '</a>';
};
// Featured collections (only those with something in them)
$featured = ['new-this-week' => 'New this week', 'closing-soon' => 'Closing in 14 days', 'no-equity' => 'No equity',
             'women-founders' => 'Women founders', 'students' => 'Students', 'above-1-crore' => '₹1 crore+',
             'under-10-lakh' => 'Up to ₹10 lakh', 'rolling' => 'Open all year', 'government' => 'Government schemes',
             'global-open-to-india' => 'Global, open to India'];
$have = [];
foreach (fg_roundups()['roundups'] as $r) $have[$r['slug']] = $r;
?>
<main class="gp-wrap" style="max-width:1160px">
  <div class="gp-crumbs"><a href="resources.html">Resources</a> › <a href="grants.php">Open grants</a><?= $key ? ' › ' . h($coll['title'] ?? $val) : '' ?></div>
  <h1 class="gp-title"><?= h($h1) ?></h1>
  <p class="gp-lede" style="max-width:760px"><?= h($lede) ?></p>
  <p style="margin:8px 0 18px;color:var(--text-muted);font-size:13px"><?= count($items) ?> <?= $key === 'week' ? 'listed' : 'open' ?> · updated <?= h(sb_fmt_date(sb_feed()['updated'] ?? '')) ?></p>

  <div class="gp-chips"><?php foreach ($featured as $slug => $label) if (!empty($have[$slug])) echo $chip('c', $slug, $label); ?></div>
  <div class="gp-chips" style="margin-top:-12px"><a<?= !$key ? ' class="on"' : '' ?> href="grants.php">All</a><?php foreach (array_keys($types) as $t) echo $chip('type', $t); ?></div>
  <div class="gp-chips" style="margin-top:-12px"><?php foreach (['Idea','Prototype','MVP','Early Traction','Growth'] as $s) if (isset($stagesAll[$s])) echo $chip('stage', $s); ?>
    <?php ksort($regions); foreach (array_keys($regions) as $r) echo $chip('region', $r); ?></div>

  <?php if (!$items): ?>
    <div class="gp-card"><p>Nothing open in this category right now. New opportunities are added every morning — <a href="grants.php">see everything that's open</a>.</p></div>
  <?php else: ?>
  <div class="gp-list">
    <?php foreach ($items as $it): ?>
      <a class="gp-item" href="<?= h(sb_grant_url($it)) ?>">
        <span class="tag tag-type"><?= h($it['type']) ?></span>
        <h3><?= h($it['title']) ?></h3>
        <div class="m"><?= h($it['provider']) ?></div>
        <div class="m"><?= h(sb_is_open($it) ? sb_deadline_text($it) : 'Closed') ?></div>
        <div class="a"><?= h($it['fundingAmount']) ?></div>
      </a>
    <?php endforeach; ?>
  </div>
  <?php endif; ?>

  <?php
  // Browse-more links: states, sectors and recent weeks (internal links help Google find every page).
  $states = array_filter(fg_roundups()['roundups'], function ($r) { return strpos($r['slug'], 'state-') === 0 || strpos($r['slug'], 'sector-') === 0; });
  $weeks  = array_slice(fg_roundups()['weekly'], 0, 6);
  if ($states || $weeks): ?>
  <section class="gp-card" style="margin-top:28px">
    <?php if ($states): ?><h2 class="gp-h2">Browse by state and sector</h2>
      <div class="gp-chips"><?php foreach ($states as $r) echo $chip('c', $r['slug'], preg_replace('/^(Startup grants and schemes in |Startup funding for )/', '', $r['title']) . ' (' . $r['count'] . ')'); ?></div><?php endif; ?>
    <?php if ($weeks): ?><h2 class="gp-h2">Added each week</h2>
      <div class="gp-chips"><?php foreach ($weeks as $w) echo $chip('week', $w['slug'], 'Week of ' . sb_fmt_date($w['from']) . ' (' . $w['count'] . ')'); ?></div><?php endif; ?>
  </section>
  <?php endif; ?>

  <section class="gp-card" style="margin-top:28px;background:var(--navy);color:var(--white);border:0">
    <h2 class="gp-h2" style="color:var(--white)">Not sure which one fits your startup?</h2>
    <p style="color:rgba(255,255,255,.8)">Tell us your stage and sector and we'll shortlist the grants you can realistically win — then help you prepare the application.</p>
    <div class="gp-actions"><a class="gp-btn gold" href="<?= h(SB_EXPERT_URL) ?>" target="_blank" rel="noopener">Talk to a Grant Expert</a>
      <a class="gp-btn ghost" href="resources.html">Use the filters &amp; deadline calendar</a></div>
  </section>
  <?php sb_author_card(); ?>
</main>
<?php sb_foot();
