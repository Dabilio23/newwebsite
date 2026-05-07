<form method="post">
  <button type="submit">Tester l'envoi</button>
</form>
<pre><?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $data = json_encode([
        'type' => 'Test',
        'nom' => 'Test depuis formulaire',
        'email' => 'test@dabil.io',
        'message' => 'Ceci est un test de send.php',
    ]);

    $opts = [
        'http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/json\r\n",
            'content' => $data,
            'ignore_errors' => true,
        ],
    ];
    $ctx = stream_context_create($opts);
    $result = file_get_contents('http://' . $_SERVER['HTTP_HOST'] . '/send.php', false, $ctx);

    echo "Requête envoyée à send.php\n";
    echo "----------------------------------------\n";

    if ($result === false) {
        echo "ÉCHEC : impossible de contacter send.php\n";
    } else {
        echo "Réponse brute :\n$result\n\n";
        $json = json_decode($result, true);
        if ($json) {
            echo "JSON décodé :\n";
            print_r($json);
            if (isset($json['success']) && $json['success'] === true) {
                echo "\n✓ SUCCÈS - Vérifie ta boîte mail marketing@dabil.io\n";
            } else {
                echo "\n✗ ÉCHEC - " . ($json['error'] ?? 'erreur inconnue') . "\n";
            }
        } else {
            echo "✗ La réponse n'est pas du JSON valide\n";
        }
    }
}
?></pre>