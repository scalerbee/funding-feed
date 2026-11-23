<?php
// Serves the daily-updated sitemap from GitHub at scalerbee.com/TheFundGuy/sitemap.php (cached 6 hours).
// Submit https://scalerbee.com/TheFundGuy/sitemap.php in Google Search Console → Sitemaps.
$cache = sys_get_temp_dir() . '/fundguy_sitemap.xml';
if (!is_file($cache) || filemtime($cache) < time() - 6 * 3600) {
    $xml = @file_get_contents('https://raw.githubusercontent.com/scalerbee/funding-feed/main/sitemap.xml');
    if ($xml && strpos($xml, '<urlset') !== false) file_put_contents($cache, $xml);
}
header('Content-Type: application/xml; charset=utf-8');
readfile($cache);
