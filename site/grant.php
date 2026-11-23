<?php
/** One page per funding opportunity: grant.php?g=<slug> */
require __DIR__ . '/funding-lib.php';

$slug = isset($_GET['g']) ? preg_replace('/[^a-z0-9-]/', '', strtolower($_GET['g'])) : '';
$it = null;
foreach (sb_feed()['items'] as $x) { if ($x['slug'] === $slug) { $it = $x; break; } }

if (!$it) {
    http_response_code(404);
    sb_head('Opportunity not found — Scaler Bee', 'This funding opportunity is no longer listed.', SB_BASE_URL . 'grants.php', true);
    echo '<div class="gp-wrap"><div class="gp-card"><h1 class="gp-title">This opportunity is no longer listed</h1>'
       . '<p class="gp-lede">It has closed or been removed. See everything that is open right now:</p>'
       . '<div class="gp-actions"><a class="gp-btn" href="grants.php">Browse open grants</a> '
       . '<a class="gp-btn ghost" href="grants.php?c=closing-soon">Closing soon</a></div></div></div>';
    sb_foot();
    exit;
}

$open    = sb_is_open($it) && ($it['active'] ?? true) !== false;
$stages  = sb_list($it['stages'] ?? '');
$sectors = sb_list($it['sectors'] ?? '');
$elig    = sb_lines($it['eligibility'] ?? '');
$bens    = sb_lines($it['benefits'] ?? '');
$where   = $it['geography'] ?? 'India';
$url     = sb_grant_url($it);

// Open opportunities are indexed. Closed ones stay indexed for 120 days after the last date
// (people keep searching "<scheme> last date" and many calls reopen yearly), then drop out.
$closedLong = !$open && (empty($it['deadline']) || strtotime($it['deadline']) < strtotime('-120 days'));
$noindex = $closedLong;
$faq = sb_auto_faq($it);

$title = !empty($it['seoTitle'])
    ? $it['seoTitle'] . ' | Scaler Bee'
    : $it['title'] . ' — ' . $it['fundingAmount'] . ($it['deadline'] ? ', last date ' . sb_fmt_date($it['deadline']) : '') . ' | Scaler Bee';
if (!$open) $title = $it['title'] . ' — Closed (' . sb_fmt_date($it['deadline']) . ') | Scaler Bee';
$desc = !empty($it['metaDescription'])
    ? $it['metaDescription']
    : $it['title'] . ' by ' . $it['provider'] . ': ' . $it['fundingAmount'] . '. ' . sb_deadline_text($it) . '. Eligibility, benefits and how to apply.';
if (!$open) $desc = $it['title'] . ' by ' . $it['provider'] . ' closed on ' . sb_fmt_date($it['deadline']) . '. Amount, eligibility and what was offered, plus similar programmes open now.';
if (strlen($desc) > 300) $desc = substr($desc, 0, 297) . '…';

$updated = sb_feed()['updated'] ?? date('Y-m-d');
$ld = [];
$ld[] = ['@context' => 'https://schema.org', '@type' => 'Article',
    'headline' => $it['title'] . ' — eligibility, deadline and how to apply',
    'description' => $desc, 'mainEntityOfPage' => $url,
    'datePublished' => $it['addedOn'] ?? $updated, 'dateModified' => $updated,
    'author' => sb_person_ld(), 'publisher' => sb_org_ld(),
    'about' => ['@type' => 'MonetaryGrant', 'name' => $it['title'],
        'funder' => ['@type' => 'Organization', 'name' => $it['provider']], 'url' => $it['applyLink']]];
$ld[] = ['@context' => 'https://schema.org', '@type' => 'BreadcrumbList', 'itemListElement' => [
    ['@type' => 'ListItem', 'position' => 1, 'name' => 'Resources', 'item' => SB_BASE_URL . 'resources.html'],
    ['@type' => 'ListItem', 'position' => 2, 'name' => 'Open grants', 'item' => SB_BASE_URL . 'grants.php'],
    ['@type' => 'ListItem', 'position' => 3, 'name' => $it['title'], 'item' => $url]]];
if ($faq) {
    $ld[] = ['@context' => 'https://schema.org', '@type' => 'FAQPage', 'mainEntity' => array_map(function ($f) {
        return ['@type' => 'Question', 'name' => $f['q'], 'acceptedAnswer' => ['@type' => 'Answer', 'text' => $f['a']]];
    }, $faq)];
}

sb_head($title, $desc, $url, $noindex, $ld);

// Collections this opportunity belongs to (from roundups.json) — internal links for readers and Google.
$colls = [];
$cache = sys_get_temp_dir() . '/fundguy_roundups.json';
if (!is_file($cache) || filemtime($cache) < time() - 3600) {
    $raw = @file_get_contents('https://raw.githubusercontent.com/scalerbee/funding-feed/main/roundups.json');
    if ($raw && json_decode($raw, true)) @file_put_contents($cache, $raw);
}
if (is_file($cache)) {
    $rj = json_decode(file_get_contents($cache), true) ?: [];
    foreach ($rj['roundups'] ?? [] as $r) {
        if ($r['count'] >= 3 && in_array($it['slug'], $r['ids'], true) && strpos($r['slug'], 'type-') !== 0) $colls[] = $r;
    }
}
?>
<main class="gp-wrap">
  <div class="gp-crumbs"><a href="resources.html">Resources</a> › <a href="grants.php">Open grants</a> › <?= h($it['title']) ?></div>

  <article>
  <div class="gp-card">
    <?php if (!$open): ?><div class="gp-closed">Applications closed on <?= h(sb_fmt_date($it['deadline'])) ?>. Many calls like this reopen each year — see what's open now below.</div><?php endif; ?>
    <div class="detail-tags">
      <?php if (!empty($it['type'])): ?><a class="tag tag-type" style="text-decoration:none" href="grants.php?type=<?= h(rawurlencode($it['type'])) ?>"><?= h($it['type']) ?></a><?php endif; ?>
      <?php foreach ($stages as $s): ?><a class="tag tag-stage" style="text-decoration:none" href="grants.php?stage=<?= h(rawurlencode($s)) ?>"><?= h($s) ?></a><?php endforeach; ?>
      <?php foreach ($sectors as $s): ?><?php if ($s === 'All sectors'): ?><span class="tag tag-sector"><?= h($s) ?></span><?php else: ?><a class="tag tag-sector" style="text-decoration:none" href="grants.php?sector=<?= h(rawurlencode($s)) ?>"><?= h($s) ?></a><?php endif; ?><?php endforeach; ?>
    </div>
    <h1 class="gp-title"><?= h($it['title']) ?></h1>
    <p class="gp-lede"><?= h($it['shortDesc'] ?? '') ?></p>
    <div class="gp-facts">
      <div class="gp-fact"><div class="l">Funding</div><div class="v money"><?= h($it['fundingAmount']) ?></div></div>
      <div class="gp-fact"><div class="l">Last date</div><div class="v"><?= h($open ? sb_deadline_text($it) : 'Closed on ' . sb_fmt_date($it['deadline'])) ?></div></div>
      <div class="gp-fact"><div class="l">Provider</div><div class="v"><?= h($it['provider']) ?></div></div>
      <div class="gp-fact"><div class="l">Open for</div><div class="v"><a href="grants.php?region=<?= h(rawurlencode($where)) ?>" style="color:inherit"><?= h($where) ?></a></div></div>
      <div class="gp-fact"><div class="l">Equity</div><div class="v"><?= h($it['fundingType'] ?? '—') ?></div></div>
      <div class="gp-fact"><div class="l">Source</div><div class="v"><?= h($it['fundingSource'] ?? '—') ?></div></div>
    </div>
    <p style="margin:10px 0 0;color:var(--text-muted);font-size:13px">Listed <?= h(sb_fmt_date($it['addedOn'] ?? $updated)) ?> · last checked <?= h(sb_fmt_date($updated)) ?></p>
    <div class="gp-actions">
      <a class="gp-btn" href="<?= h($it['applyLink']) ?>" target="_blank" rel="noopener">Official page ↗</a>
      <a class="gp-btn gold" href="<?= h(SB_EXPERT_URL) ?>" target="_blank" rel="noopener">Talk to a Grant Expert</a>
    </div>
  </div>

  <?php if ($elig): ?>
  <section class="gp-card"><h2 class="gp-h2">Who can apply</h2>
    <ul><?php foreach ($elig as $e): ?><li><?= h($e) ?></li><?php endforeach; ?></ul></section>
  <?php endif; ?>

  <?php if ($bens): ?>
  <section class="gp-card"><h2 class="gp-h2">What you get</h2>
    <ul><?php foreach ($bens as $b): ?><li><?= h($b) ?></li><?php endforeach; ?></ul>
    <?php if (!empty($it['about'])): ?><p style="margin-top:12px;color:var(--text-muted)"><?= h($it['about']) ?></p><?php endif; ?>
  </section>
  <?php endif; ?>

  <?php if ($faq): ?>
  <section class="gp-card gp-faq"><h2 class="gp-h2">Quick answers</h2>
    <?php foreach ($faq as $f): ?>
      <details open><summary><?= h($f['q']) ?></summary><p><?= h($f['a']) ?></p></details>
    <?php endforeach; ?>
  </section>
  <?php endif; ?>

  <section class="gp-card" style="background:var(--navy);color:var(--white);border:0">
    <h2 class="gp-h2" style="color:var(--white)">Want a stronger application?</h2>
    <p style="color:rgba(255,255,255,.8)">Grant committees reject most applications for fixable reasons: a vague use of funds, weak financials or a deck that buries the traction. Scaler Bee prepares grant write-ups, financial models and pitch decks for founders.</p>
    <div class="gp-actions">
      <a class="gp-btn gold" href="<?= h(SB_EXPERT_URL) ?>" target="_blank" rel="noopener">Talk to a Grant Expert</a>
      <a class="gp-btn ghost" href="<?= h(SB_PITCH_URL) ?>" target="_blank" rel="noopener">Get my pitch reviewed</a>
    </div>
  </section>

  <?php sb_author_card(); ?>
  </article>

  <?php if ($colls): ?>
  <section style="margin-top:28px"><h2 class="gp-h2">More lists this appears in</h2>
    <div class="gp-chips"><?php foreach (array_slice($colls, 0, 8) as $c): ?><a href="grants.php?c=<?= h($c['slug']) ?>"><?= h($c['title']) ?> (<?= (int)$c['count'] ?>)</a><?php endforeach; ?></div>
  </section>
  <?php endif; ?>

  <?php
  // Related open opportunities: same region first, then same type, excluding this one.
  $pool = array_values(array_filter(sb_open_items(), function ($x) use ($it) { return $x['slug'] !== $it['slug']; }));
  usort($pool, function ($a, $b) use ($it, $where) {
      $sa = (($a['geography'] ?? '') === $where ? 2 : 0) + ($a['type'] === $it['type'] ? 1 : 0);
      $sb = (($b['geography'] ?? '') === $where ? 2 : 0) + ($b['type'] === $it['type'] ? 1 : 0);
      return $sb <=> $sa;
  });
  $rel = array_slice(array_filter($pool, function ($x) use ($it, $where) { return $x['type'] === $it['type'] || ($x['geography'] ?? '') === $where; }), 0, 6);
  if ($rel): ?>
  <section style="margin-top:28px"><h2 class="gp-h2"><?= $open ? 'Other open opportunities' : 'Similar programmes open now' ?></h2>
    <div class="gp-list">
    <?php foreach ($rel as $r): ?>
      <a class="gp-item" href="<?= h(sb_grant_url($r)) ?>">
        <span class="tag tag-type"><?= h($r['type']) ?></span>
        <h3><?= h($r['title']) ?></h3>
        <div class="m"><?= h(sb_deadline_text($r)) ?></div>
        <div class="a"><?= h($r['fundingAmount']) ?></div>
      </a>
    <?php endforeach; ?>
    </div></section>
  <?php endif; ?>
</main>
<?php sb_foot();
