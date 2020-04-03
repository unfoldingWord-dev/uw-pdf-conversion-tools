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
$sort = isset($_GET['sort'])?$_GET['sort']:'date';
$dirs = array();
$dir = opendir("."); // open the cwd..also do an err check.
while(false != ($subdir = readdir($dir))) {
       if(is_dir($subdir) && ! in_array($subdir, [".", "..", "css", "images", "save", "log"])) {
            $stat = stat("./$subdir");
            $data = array(
                'name'=>$subdir,
                'mtime'=>$stat['mtime'],
            );
            $subdir_dir = opendir($subdir); // open the cwd..also do an err check.
            $files = array();
            while(false != ($subfile = readdir($subdir_dir))) {
                $filepath= './'.$subdir.'/'.$subfile;
                if(is_link($filepath)) {
                    $stat = stat($filepath);
                    $files[] = array(
                        'name'=>$subfile,
                        'mtime'=>$stat['mtime'],
                    );
                }
            }
            if ($files) {
                usort($files, function($a, $b) {return $a['mtime'] > $b['mtime'] ? -1 : ($a['mtime'] == $b['mtime'] ? 0 : 1);});
                $data['files'] = $files;
                $data['mtime'] = $files[0]['mtime'];
                $dirs[] = $data;
            }
       }
}

usort($dirs, function($a, $b) {
   global $sort;
   if($sort=='date') {
     return $a['mtime'] > $b['mtime'] ? -1 : ($a['mtime'] == $b['mtime'] ? 0 : 1);
   } else {
     return strnatcmp($a['name'], $b['name']);
   }
});

echo '<div class="sort">Sort by: '.($sort=='name'?'<strong>Name</strong>':'<a href="?sort=name">Name</a>').' | '.($sort=='date'?'<strong>Last Generated</strong>':'<a href="?sort=date">Last Generated</a>').'</div>';
echo '<div><h1 style="padding-bottom:0;margin-bottom:0">Resources:</h1>';
echo '<p>(Sorted by '.($sort=='date'?'date last generated, descending':'name, ascending').')</p>';
echo '<div class="menu">';
foreach($dirs as $data) {
    $files = $data['files'];
    if ($files) {
        $mtime = $files[0]['mtime'];
        echo '<div class="item"><a class="menu-item" href="#'.$data['name'].'">'.$data['name'].'</a><br/><em>('.date("Y-m-d", $mtime).')</em></div>'."\n";
    }
}
echo '</div></div>';

// print.
foreach($dirs as $data) {
    $files = $data['files'];
    $dir = $data['name'];

    if ($files) {
        usort($files, function($a, $b) {
            global $sort;
            if($sort=='date') {
                return $a['mtime'] > $b['mtime'] ? -1 : ($a['mtime'] == $b['mtime'] ? 0 : 1);
            } else {
                return strnatcmp($a['name'], $b['name']);
            }
        });
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
