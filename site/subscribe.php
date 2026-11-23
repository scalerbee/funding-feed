<?php
// The Fund Guy: email alert sign-up -> Brevo list (with stage / sector / state preferences).
require __DIR__ . '/_config.php';
header('Content-Type: application/json; charset=utf-8');

function out($ok, $msg, $code = 200) { http_response_code($code); echo json_encode(['ok' => $ok, 'message' => $msg]); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(false, 'Use the form to subscribe.', 405);
if (!empty($_POST['website'])) out(true, 'Thanks!');                       // honeypot: bots fill this hidden field

$email = trim(strtolower($_POST['email'] ?? ''));
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 120) out(false, 'Please enter a valid email address.', 400);

$stages  = ['any', 'Idea', 'Prototype', 'MVP', 'Revenue', 'Growth'];
$sectors = ['any', 'ai', 'climate', 'health', 'agri', 'fintech', 'social-impact', 'mobility', 'defence'];
$stage  = in_array($_POST['stage'] ?? 'any', $stages, true) ? $_POST['stage'] : 'any';
$sector = in_array($_POST['sector'] ?? 'any', $sectors, true) ? $_POST['sector'] : 'any';
$state  = preg_replace('/[^A-Za-z &]/', '', $_POST['state'] ?? 'any');
if ($state === '' ) $state = 'any';

// Basic rate limit: max 5 sign-ups per IP per hour.
$rl = sys_get_temp_dir() . '/fg_sub_' . md5($_SERVER['REMOTE_ADDR'] ?? 'x');
$hits = array_filter(is_file($rl) ? explode(',', file_get_contents($rl)) : [], fn($t) => (int)$t > time() - 3600);
if (count($hits) >= 5) out(false, 'Too many attempts. Please try again later.', 429);
$hits[] = time(); @file_put_contents($rl, implode(',', $hits));

$payload = [
    'email' => $email,
    'attributes' => ['FG_STAGE' => $stage, 'FG_SECTOR' => $sector, 'FG_STATE' => $state],
    'listIds' => [(int)BREVO_LIST_ID],
    'updateEnabled' => true,
];
$ch = curl_init('https://api.brevo.com/v3/contacts');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 15,
    CURLOPT_HTTPHEADER => ['api-key: ' . BREVO_API_KEY, 'Content-Type: application/json', 'Accept: application/json'],
    CURLOPT_POSTFIELDS => json_encode($payload),
]);
$res = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($code >= 200 && $code < 300) out(true, "You're in! Every week we'll email you the opportunities that fit your startup.");
error_log('Fund Guy subscribe failed: HTTP ' . $code . ' ' . $res);
out(false, 'Sorry, something went wrong. Please try again in a minute.', 502);
