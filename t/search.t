#!/usr/bin/env perl
use strict;

use Test::More tests => 22;

use IO::File;
use File::Path qw(rmtree);
use File::Spec::Functions qw(catdir catfile rel2abs splitdir);

#----------------------------------------------------------------------
# Load search.cgi

my @path = splitdir(rel2abs($0));
pop(@path);
pop(@path);

my $lib = catdir(@path);
unshift(@INC, $lib);

require 'search.cgi';

my $test_dir = catdir(@path, 'test');

rmtree($test_dir);
mkdir $test_dir;
chdir($test_dir);

#----------------------------------------------------------------------
# Create test data and test slurp

do {
    my $template = <<'EOQ';
<html>
<head>
<title>Page %1</title>
</head>
<body>
  <!-- section content -->
  <p>This is the
  %2 page. It is not the fourth page.</p> 
  <!-- endsection content -->  
</body>
</html>
EOQ

    for my $count (qw(first second third)) {
        my $text = $template;
        my $ucount = ucfirst($count);
        $text =~ s/%1/$ucount/g;
        $text =~ s/%2/$count/g;

        my $file = "$count.html";
        my $out = IO::File->new($file, 'w');
        print $out $text;
        close $out;
        
        my $result = SearchEngine::slurp($file);
        is($result, $text, "test slurp on $file") # test 1-3
    }
};

#----------------------------------------------------------------------
# Test scrub_parameter

do {
    my $param = 'foobar foobiz';
    my $result = SearchEngine::scrub_parameter($param);
    is($result, $param, 'scrub_parameter with valid string'); # test 4
    
    $param = "<$param>";
    $result = SearchEngine::scrub_parameter($param);
    is($result, '', 'scrub_parameter with invalid string'); # test 5
};

#----------------------------------------------------------------------
# Test globbify

do {
    my $pattern = ['*.html', '*.pdf'];
    my $result = SearchEngine::globbify($pattern);
    is($result, '(^.*\.html$)|(^.*\.pdf$)', 'globbify'); # test 6
};

#----------------------------------------------------------------------
# Test build_url

do {
    my $base_url = 'http://www.example.com';
    my $filename = rel2abs('one.html');
    
    my $result = SearchEngine::build_url($base_url, $test_dir, $filename);
    is($result, "$base_url/one.html", 'build_url'); # test 7
};

#----------------------------------------------------------------------
# Test encode_url

do {
    my $title = 'My Title';
    my $summary = '"My Summary"';
    my $url = 'http://www.example/com/search.cgi';
    my %param = (title => $title, summary => $summary);
    
    my $result = SearchEngine::encode_url($url, %param);
    my $result_ok = "$url?summary=$summary&title=$title";
    $result_ok =~ s/ /+/g;
    $result_ok =~ s/\"/%22/g;
    
    is($result, $result_ok, 'encode_url'); # test 8
};

#----------------------------------------------------------------------
# Test get_context

do {
    my $text = 'aa bbb cc ' x 8;
    $text .= 'dd eee ff ' x 4;
    $text .= 'gg hhh ii ' x 8;
    
    my $result_ok = 'aa bbb cc ' x 4;
    $result_ok .= 'dd eee ff ' x 4;
    $result_ok =~ s/dd/<b>dd<\/b>/g;
    $result_ok =~ s/^aa //;
    $result_ok =~ s/\s+$//;
    
    my $result = SearchEngine::get_context($text, 'dd', 80);
    is($result, $result_ok, 'get_context');  #test 9  
};

#----------------------------------------------------------------------
# Test parse_sections, substitute_sections, and parse_htmldoc

do {
    my $text =<<'EOQ';
<html>
<head>
<!-- section header -->
<title>My Title</title>
<!-- endsection header -->
</head>
<body>
<!-- section content -->
<p>My content.</p>
<!-- endsection content -->  
</body>
</html>
EOQ

    my $template =<<'EOQ';
<html>
<head>
<meta charset="utf-8">
<!-- section header -->
<!-- endsection header -->
</head>
<body class="foo">
<!-- section content -->
<!-- endsection content -->  
</body>
</html>
EOQ

    my $section = SearchEngine::parse_sections($text);
    my $section_ok = {header => "\n<title>My Title</title>\n",
                      content => "\n<p>My content.</p>\n"};
    
    is_deeply($section, $section_ok, 'parse_sections'); # test 10
    
    my ($title, $body) = SearchEngine::parse_htmldoc($text);
    is($title, 'My Title', 'parse_htmldoc title'); # test 11
    is($body, "\nMy content.\n", 'parse_htmldoc body'); # test 12
    
    my $result = SearchEngine::substitute_sections($template, $section);
    like($result, qr(charset), 'substitute_sections, template code'); # test 13
    like($result, qr(My content), 'substitute_sections, section code'); # test 14
};

#----------------------------------------------------------------------
# Test do_search

do {
    my $base_url = 'http://www.example.com';
    my $result = SearchEngine::do_search($base_url, $test_dir, 'first');

    delete $result->[0]{modtime};
    my $result_ok = [{title => 'Page First',
                      count => 1,
                      context => 'This is the <b>first</b> page. It is not the fourth page.',
                      url => "$base_url/first.html"}];

    is_deeply($result, $result_ok, 'do_search'); # test 15   
};

#----------------------------------------------------------------------
# Test restrict_pages and navlinks
do {
    my @subset;
    my @results;
    for my $i (1..100) {
        my $result = {count => 1, modtime => 1000 - $i, i => $i};
        push(@results, $result);
        push(@subset, $result) if $i <= 20;
    }

    my $query = 'foobar';
    my $url = 'search.cgi';
    my $hash = {query => $query, script_url => $url};

    my $restricted = SearchEngine::restrict_page($hash, \@results);
    
    my %restricted_ok = (%$hash, total => 100, start => 1, finish => 20);
    $restricted_ok{results} = \@subset;

    is_deeply($restricted, \%restricted_ok, 'restrict_page'); # test 16

    $restricted = SearchEngine::navlinks($restricted);
    is($restricted->{next_url}, "$url?query=$query&start=21",
       'navlinks next'); # test 17
};

#----------------------------------------------------------------------
# Test parse_code

do {
    my $text = <<'EOT';
<!-- for @results -->
<!-- if $x == 1 -->
\$x is $x (one)
<!-- elsif $x == 2 -->
\$x is $x (two)
<!-- else -->
\$x is unknown
<!-- endif -->
<!-- endfor -->
EOT

my $result_ok = <<'EOT';
foreach my $data (@{$data->{results}}) {
if ($data->{x} == 1) {
$text .= <<"EOQ";
\$x is $data->{x} (one)
EOQ
} elsif ($data->{x} == 2) {
$text .= <<"EOQ";
\$x is $data->{x} (two)
EOQ
} else {
$text .= <<"EOQ";
\$x is unknown
EOQ
}
}
EOT

    my @lines = split(/\n/, $text);
    my @result_ok = split(/\n/, $result_ok);
    my @result = SearchEngine::parse_code(\@lines);
    is_deeply(\@result, \@result_ok, 'parse_code'); # test 18
};

#----------------------------------------------------------------------
# Test for loop

do {
    my $template = <<'EOQ';
<!-- for @list -->
$name $phone
<!-- endfor -->
EOQ
    
    my $sub = SearchEngine::compile_code($template);
    my $data = {list => [{name => 'Ann', phone => '4444'},
                         {name => 'Joe', phone => '5555'}]};
    
    my $text = $sub->($data);
    
    my $text_ok = <<'EOQ';
Ann 4444
Joe 5555
EOQ
    
    is($text, $text_ok, "compile_code for loop"); # test 19
};

#----------------------------------------------------------------------
# Test if blocks

do {
    my $template = <<'EOQ';
<!-- if $x == 1 -->
\$x is $x (one)
<!-- elsif $x  == 2 -->
\$x is $x (two)
<!-- else -->
\$x is unknown
<!-- endif -->
EOQ
    
    my $sub = SearchEngine::compile_code($template);
    
    my $data = {x => 1};
    my $text = $sub->($data);
    is($text, "\$x is 1 (one)\n", "compile_code if block"); # test 20
    
    $data = {x => 2};
    $text = $sub->($data);
    is($text, "\$x is 2 (two)\n", "compile_code elsif block"); # test 21
    
    $data = {x => 3};
    $text = $sub->($data);
    is($text, "\$x is unknown\n", "compile_code else block"); # test 22
};
