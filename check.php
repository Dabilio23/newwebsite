<pre><?php
echo "Fichier: " . __FILE__ . "\n";
echo "Date modif: " . date('Y-m-d H:i:s', filemtime(__FILE__)) . "\n";
echo "MD5 hash: " . md5_file(__FILE__) . "\n\n";

$send = __DIR__ . '/send.php';
if (file_exists($send)) {
    echo "send.php existe: oui\n";
    echo "Date modif send.php: " . date('Y-m-d H:i:s', filemtime($send)) . "\n";
    echo "MD5 send.php: " . md5_file($send) . "\n";
} else {
    echo "send.php existe: NON\n";
}

$env = __DIR__ . '/.env';
if (file_exists($env)) {
    echo ".env existe: oui\n";
    echo "Contenu .env:\n";
    echo file_get_contents($env) . "\n";
} else {
    echo ".env existe: NON\n";
}
?></pre>