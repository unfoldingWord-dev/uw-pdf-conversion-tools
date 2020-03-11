<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Resource list</title>
  </head>
<body>
<?php
date_default_timezone_set('US/Eastern');
$dirs = array();
$dir = opendir("."); // open the cwd..also do an err check.
while(false != ($subdir = readdir($dir))) {
        if(($subdir != ".") && ($subdir != "..") && is_dir($subdir) && ($subdir != "images") {
                $dirs[] = $subdir; // put in array.
        }
}

natsort($dirs); // sort.

echo '<p>';
foreach($dirs as $dir) {
    echo '<a href="#'.$dir.'">'.$dir.'</a>'."<br/>\n";
}
echo '</p>';

// print.
foreach($dirs as $dir) {
    $files = array();
    $subdir = opendir($dir); // open the cwd..also do an err check.
    while(false != ($subfile = readdir($subdir))) {
        $filepath= './'.$dir.'/'.$subfile;
        if(($subfile != ".") && ($subfile != "..") && ($subfile != "index.php") && is_link($filepath) && !is_dir($filepath) && ($subfile != "css")) {
                $files[] = $subfile; // put in array.
        }
    }

    if ($files) {
        natsort($files); // sort.

        echo "<h2 id='".$dir."'>".$dir."</h2>\n";
        echo "<p>\n";
        foreach($files as $file) {
            $filepath = './'.$dir.'/'.$file;
            $realfile = './'.$dir.'/'.basename(readlink($filepath));

            echo '<a href="'.$realfile.'">'.basename($realfile).'</a> <em>('.date ("Y-m-d H:i:s", filemtime($filepath)).')</em><br/>'."\n";
        }
        echo "</p>\n";
    }
}
?>
</body>
</html>
