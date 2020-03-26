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
$sort_by_sort = function($a, $b) {
   if($_GET['sort']=='date') {
     return $a['mtime'] > $b['mtime'] ? -1 : ($a['mtime'] == $b['mtime'] ? 0 : 1);
   } else {
     return strnatcmp($a['name'], $b['name']);
   }
};

date_default_timezone_set('US/Eastern');
$dirs = array();
$dir = opendir("."); // open the cwd..also do an err check.
while(false != ($subdir = readdir($dir))) {
       if(is_dir($subdir) && ! in_array($subdir, [".", "..", "css", "images", "save", "log"])) {
            $stat = stat("./$subdir");
            $dirs[] = array(
                'name'=>$subdir,
                'mtime'=>$stat['mtime']
            );
       }
}

usort($dirs, $sort_by_sort);

echo '<div class="sort">Sort: <a href="?sort=name">name</a> | <a href="?sort=date">last generated</a></div>';
echo '<div><h1>Resources:</h1><div class="menu">';
foreach($dirs as $data) {
    echo '<div class="item"><a class="menu-item" href="#'.$data['name'].'">'.$data['name'].'</a><br/><em>('.date("Y-m-d", $data['mtime']).')</em></div>'."\n";
}
echo '</div></div>';

// print.
foreach($dirs as $data) {
    $files = array();
    $dir = $data['name'];
    $subdir = opendir($dir); // open the cwd..also do an err check.
    while(false != ($subfile = readdir($subdir))) {
        $filepath= './'.$dir.'/'.$subfile;
        $stat = stat("./$filepath");
        if(is_link($filepath)) {
                $files[] = array(
                    'name'=>$subfile,
                    'mtime'=>$stat['mtime'],
                );
        }
    }

    if ($files) {
        usort($files, $sort_by_sort);
        echo "<h2 id='".$dir."'>".$dir."</h2>\n";
        echo "<p>\n";
        foreach($files as $file_data) {
            $file = $file_data['name'];
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
