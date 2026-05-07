<form method="post">
  <button type="submit">Tester l'envoi</button>
</form>
<pre><?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $payload = json_encode([
        'type' => 'Test',
        'nom' => 'Test depuis formulaire',
        'email' => 'test@dabil.io',
        'message' => 'Ceci est un test de send.php',
    ]);

    $ch = curl_init('https://' . $_SERVER['HTTP_HOST'] . '/send.php');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_FOLLOWLOCATION => true,
    ]);
    $result = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    echo "HTTP $httpCode\n";
    echo "----------------------------------------\n";

    if ($error) {
        echo "cURL error: $error\n";
    } elseif (!$result) {
        echo "Réponse vide\n";
    } else {
        echo "$result\n\n";
        $json = json_decode($result, true);
        if ($json && isset($json['success']) && $json['success'] === true) {
            echo "✓ SUCCÈS - Vérifie ta boîte mail marketing@dabil.io\n";
        } else {
            echo "✗ ÉCHEC - " . ($json['error'] ?? 'réponse inattendue') . "\n";
        }
    }
}
?></pre>