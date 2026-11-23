<?php
// Loads fundguy-config.php from the cPanel home folder (preferred) or from this folder.
foreach ([dirname(__DIR__, 2) . '/fundguy-config.php', dirname(__DIR__) . '/fundguy-config.php', __DIR__ . '/fundguy-config.php'] as $f) {
    if (is_file($f)) { require_once $f; return; }
}
http_response_code(500);
exit('Configuration missing.');
