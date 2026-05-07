<?php
ob_start();

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

function jsonResponse($code, $data) {
    if (ob_get_level()) ob_clean();
    http_response_code($code);
    echo json_encode($data);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    jsonResponse(200, []);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    jsonResponse(405, ['error' => 'Method not allowed']);
}

$raw = file_get_contents('php://input');
$input = json_decode($raw, true);
if (!$input || !isset($input['type'])) {
    jsonResponse(400, ['error' => 'Invalid request']);
}

$type = $input['type'];
unset($input['type']);

$subject = "[$type] Nouveau message depuis dabil.io";

$lines = ["Type: $type", '---'];
foreach ($input as $key => $value) {
    $lines[] = "$key: $value";
}
$text = implode("\n", $lines);

$apiKey = getenv('RESEND_API_KEY');
if (!$apiKey) {
    $envFile = __DIR__ . '/.env';
    if (file_exists($envFile)) {
        $lines = @file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if ($lines) {
            foreach ($lines as $line) {
                $line = trim($line);
                if ($line === '' || $line[0] === '#') continue;
                $parts = explode('=', $line, 2);
                if (count($parts) === 2 && trim($parts[0]) === 'RESEND_API_KEY') {
                    $apiKey = trim($parts[1]);
                    break;
                }
            }
        }
    }
}

if (!$apiKey) {
    error_log('send.php: RESEND_API_KEY not found in env or .env file');
    jsonResponse(500, ['error' => 'Erreur de configuration serveur']);
}

$ch = curl_init('https://api.resend.com/emails');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'Authorization: Bearer ' . $apiKey,
        'Content-Type: application/json',
    ],
    CURLOPT_POSTFIELDS => json_encode([
        'from' => 'Dabilio <hello@dabil.io>',
        'to' => ['marketing@dabil.io'],
        'subject' => $subject,
        'text' => $text,
    ]),
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($curlError) {
    error_log('send.php: cURL error - ' . $curlError);
    jsonResponse(500, ['error' => 'Erreur d\'envoi du message']);
}

if ($httpCode >= 400) {
    error_log('send.php: Resend API error (HTTP ' . $httpCode . ') - ' . $response);
    jsonResponse(500, ['error' => 'Erreur d\'envoi du message']);
}

jsonResponse(200, ['success' => true]);
