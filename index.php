<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Resource list</title>
    <style>
body {
  background-color: white;
  padding: 1em;
}

.menu {
  -webkit-column-width: 150px;
  -moz-column-width: 150px;
  column-width: 150px;
}

.item {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
    -webkit-column-break-inside: avoid !important;
    column-break-inside: avoid: !important;
}
</style>
  </head>
<body>
<?php
date_default_timezone_set('US/Eastern');
$dirs = array();
$dir = opendir("."); // open the cwd..also do an err check.
while(false != ($subdir = readdir($dir))) {
        if(is_dir($subdir) && ! in_array($subdir, [".", "..", "css", "images", "save", "log"])) {
                $dirs[] = $subdir; // put in array.
        }
}

natsort($dirs); // sort.
echo 'Modification time: ' . $stat['mtime']; // will show unix time stamp.

echo '<div><h1>Resources:</h1><div class="menu">';
foreach($dirs as $dir) {
    $stat = stat("./$dir");
    echo '<div class="item"><a class="menu-item" href="#'.$dir.'">'.$dir.'</a><br/><em>('.date("Y-m-d", $stat['mtime']).')</em></div>'."\n";
}
echo '</div></div>';

// print.
foreach($dirs as $dir) {
    $files = array();
    $subdir = opendir($dir); // open the cwd..also do an err check.
    while(false != ($subfile = readdir($subdir))) {
        $filepath= './'.$dir.'/'.$subfile;
        if(is_link($filepath)) {
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
