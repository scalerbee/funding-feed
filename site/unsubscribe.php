<?php
// The Fund Guy: one-click unsubscribe from the weekly alerts (link in every email).
require __DIR__ . '/_config.php';
$email = strtolower(trim($_GET['e'] ?? $_POST['e'] ?? ''));
$token = $_GET['t'] ?? $_POST['t'] ?? '';
$valid = filter_var($email, FILTER_VALIDATE_EMAIL) && hash_equals(substr(hash_hmac('sha256', $email, UNSUB_SECRET), 0, 32), $token);
$done = false;
if ($valid) {
    $ch = curl_init('https://api.brevo.com/v3/contacts/lists/' . (int)BREVO_LIST_ID . '/contacts/remove');
    curl_setopt_array($ch, [
        CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15,
        CURLOPT_HTTPHEADER => ['api-key: ' . BREVO_API_KEY, 'Content-Type: application/json', 'Accept: application/json'],
        CURLOPT_POSTFIELDS => json_encode(['emails' => [$email]]),
    ]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $done = ($code >= 200 && $code < 300) || $code == 400; // 400 = already removed
}
if ($_SERVER['REQUEST_METHOD'] === 'POST') { http_response_code($done ? 200 : 400); exit; } // one-click (List-Unsubscribe-Post)
?><!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Unsubscribe | The Fund Guy</title>
<style>body{font-family:Arial,Helvetica,sans-serif;background:#f6f7f9;margin:0;padding:48px 16px;color:#222}main{max-width:480px;margin:auto;background:#fff;border-radius:8px;padding:28px;text-align:center}a{color:#1a56db}</style></head>
<body><main>
<?php if ($done): ?><h1>You're unsubscribed</h1><p>You won't get The Fund Guy weekly alerts any more.</p>
<?php else: ?><h1>Link not valid</h1><p>This unsubscribe link is broken or expired. Reply to any of our emails and we'll remove you by hand.</p><?php endif; ?>
<p><a href="https://scalerbee.com/TheFundGuy/resources.html">Back to The Fund Guy</a></p></main></body></html>
