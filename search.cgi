#!/usr/bin/perl

=pod

=head1 NAME

search.cgi -- Search engine for web sites

=head1 AUDIENCE

This search engine is intended for web masters with small static sites
(up to 1000 pages) under a single directory tree. It is installed as a
cgi script, so your ISP must allow you to install your own cgi scripts
in order to use it.

=head1 INSTALLATION

Before installing the script, you should find out from your ISP what
extension should be used for a Perl cgi script and what is the
location of Perl on your ISP's system. This information will probably
be available in the FAQ. If the top line of this file does not match
the location of Perl on your ISP's system, edit it so it does. If your
web pages do not end with the extension '.html', edit the value of
DO_SEARCH to have the correct extension.

Ftp this file into the top level html directory on your system. If
your ISP does not allow you to place cgi scripts in this directory,
place this script in the directory your ISP indicates and follow the
instructions on setting BASE_URL and BASE_DIRECTORY in the
customization section.

Use the ftp client to give this file executable permission. Once all
that is done, test the script by typing its url, something like

 http://www.yoursite.com/search.cgi

You should see a search form with instructions on how to use it. Enter
a search term and press return. You should now have a working search
engine on your site.

You can simply add a link to the search engine from your web site or
you can add a form which calls the search engine. Here is an example
of the html code to add to your site for the form.

    <form method="post" action="search.cgi">
    <input type="text" name="query" value="" size="20" />
    </form>

=head1 CUSTOMIZATION

Although you should now have a functioning search engine, you probably
will want to change how it looks and acts. You can do this by editing
the scripts configuration variables and by creating html template files
for the search engine.

The constants DO_SEARCH and DONT_SEARCH control which files the search
engine looks at. They contain filename wildcard patterns. If you want
to use more than one pattern you can create an array of patterns,
which is a comma separated list surrounded by square brackets. For
example

    ['*.htm', '*.html']

By default the search engine searches the directory containing the
script and all its subdirectories. If your ISP does not allow you to
place scripts in the top html directory, set BASE_DIRECTORY and
BASE_URL to the complete path and the url of the top html directory.

The look of the search page is controlled by an html template file. By
default the search engine uses the template afterthe __DATA__
statement at the end of the program. You can create your own template,
put its name in the constant SEARCH_TEMPLATE and ftp it to your web
site in the same directory as this script.

One reason you may wish to use your own template is to give the search
results the look of your web site. To do this, take a typical web page
on your site, strip out the content unique to the page, and replace it
with the portion of the template below between the body tags.

The template can be customized further to make it look the way you
wish. The template commands and variables are described in the next
section.

This script allows you to create a site wide template so that you can
have a common look for all the web pages and cgi scripts on your
site. If you wish to use this optional feature, set the value of
SITE_TEMPLATE to the name of your site wide template. Blocks in the
site template are wrapped in html comments that look like

    <!-- section name -->
    <!-- endsection name -->

where name is any identifier string. Block delimeted in the same
comments in the search template replace the sections in the site
template.

BODY_TAG indicates the section in the web page that is searched for
matches. 

The search engine divides its results into separate pages with links
to the next and previous pages of results, where appropriate. The
number of results displayed on each page is controlled by
NUMBER_RESULTS.

The search results display an extract from the matched page containing
the first search term so you can see the term in its context. The
length of this extract is set by CONTEXT_LENGTH.

The parameters QUERY_PARAM and START_PARAM set the names of the cgi
parameters used by this script. You will probably not need to change
them.

The parameter COMMANDS contains the commands recognized by the template
engine and their translation into Perl. Do not change it unless you
understand how the template engine works.

=head1 TEMPLATE CUSTOMIZATION

This script builds the web page it outputs by filling in values in a
template. The default template is at the end of the file. Whenever a
string like $name occurs in the template, it is replaced by the
corresponding value generated by this script. The template also uses
simple control structures: the for and endfor statements that loop
over the results returned by the search engine and the if, else, 
elsif, and endif statement that include code conditionally in the output,
depending on the value of the variable on the if statement.

All control structures must be contained in html comments, which must
be the first text on the  template line. The comment must be the only
text on the line and be contained on a single line.

This script produces the results array, whose contents are looped over
to display the search results. The following variables can be used in
the template lines between the "for @results" and "endfor" lines: 

=over 4

=item url

The url of the web page matched in the search

=item title

The title of the web page

=item context

A string displaying the search term in context

=item count

The number of times the search terms occured in the page

=back

The other variables calculated by the search script can be used
outside the loop. These variables are:

=over 4

=item query

The search string

=item query_param

The name of the parameter containing the search string

=item base_url

The url of the topmost directory to search in

=item search url

The url of this script

=item start

The index of the first result to display, counting from one

=item finish

The index of the last result to display

=item total

The total number of results returned

=item previous_url

The url of the revious page of search results. Empty string if none

=item next_url

The url of the next page of results. Empty string if none

=back

=head1 AUTHOR

Bernie Simon (bernie.simon@gmail.com)
 
=head1 LICENSE

Copyright Bernard Simon, 2005 & 2014 under the Perl Artistic License.

=cut

package SearchEngine;

use strict;
use warnings;

use CGI qw(:standard);
use CGI::Carp 'fatalsToBrowser';
use Cwd;
use File::Find;
use FileHandle;
use File::Spec::Functions qw(abs2rel catfile rel2abs splitdir);
use Text::ParseWords;

our $VERSION = '1.01';

#----------------------------------------------------------------------
# Configuration variables

# Filename pattern of files to include in search. Can be an array
use constant DO_SEARCH => '*.html';

# Filename pattern of files to exclude from search. Can be an array
use constant DONT_SEARCH => '';

# Base directory of documents searched
use constant BASE_DIRECTORY => '';

# Base URL of documents searched
use constant BASE_URL => '';

# Template used to display results
use constant SEARCH_TEMPLATE => '';

# Template used to give page the site's look
use constant SITE_TEMPLATE => '';

# Section tag that marks the start and end of the page text
use constant BODY_TAG => 'content';

# The number of results to be displayed on each page
use constant NUMBER_RESULTS => 20;

# Length of displayed context
use constant CONTEXT_LENGTH => 80;

# Name of parameter containing query
use constant QUERY_PARAM => 'query';

# Name of parameter containing start position
use constant START_PARAM => 'start';

# The commands recognized by the template engine and their translations
use constant COMMANDS => {
                            for => 'foreach my $data (%%) {',
                            endfor => '}',
                            if => 'if (%%) {',
                            elsif => '} elsif (%%) {',
                            else => '} else {',
                            endif => '}',
                         };

#----------------------------------------------------------------------
# Call main if run as a script (no caller)

main(@ARGV) if ! caller() || (caller)[0] eq 'DB';

#----------------------------------------------------------------------
# Main procedure

sub main {
    my @args = @_;
    
    $| = 1;
    my $hash = {};
    
    # Read and untaint CGI parameters
    
    my $cgi = CGI->new ();
    
    my($query, $start);
    if (@args) {
        $query = join(' ', @args);
        $start = 0;
    } else {
        $query = $cgi->param(QUERY_PARAM);
        $start = $cgi->param(START_PARAM);
    }
    
    $query = scrub_parameter($query);
    $start = scrub_parameter($start);
        
    # Set configuration variables if left empty
    
    my $base_directory = BASE_DIRECTORY || cwd();
    my $base_url = BASE_URL || $ENV{SCRIPT_URI} || '';
    $base_url =~ s!/[^/]*$!!;
    
    # Perform the search and put results into an array
    
    my @term = map ('\b'.quotemeta($_).'\b', shellwords ($query));
    my $results = do_search($base_url, $base_directory, @term);
    
    # Add extra info used in the output page
    
    $hash->{query} = $query;
    $hash->{query_param} = QUERY_PARAM;

    $hash->{base_url} = "$base_url/";
    $hash->{script_url} = $ENV{SCRIPT_URI} ||
                          build_url($base_url, $base_directory, $0);
    
    # Build navigation links 
    
    $hash = restrict_page ($hash, $results, $start);
    $hash = navlinks ($hash);
    
    # Generate output page and print it
    
    my $text = slurp(SEARCH_TEMPLATE) || slurp(\*DATA);
    my $sub = compile_code($text);
    my $output = &$sub($hash);
    
    if (SITE_TEMPLATE) {
        my $section = parse_sections($output);
        my $text = slurp(SITE_TEMPLATE);
        $output = substitute_sections ($text, $section);
    }
    
    print "Content-type: text/html\n\n";
    print $output;
    return;
}

#----------------------------------------------------------------------
# Build the page url from the base url and filname

sub build_url {
    my ($base_url, $base_directory, $filename) = @_;

    $filename = abs2rel($filename, $base_directory);
    my @path = splitdir($filename);

    return return join('/', $base_url, @path);
}

#----------------------------------------------------------------------
# Compile a subroutine from the code embedded in the template

sub compile_code {
    my ($text) = @_;

    my @lines = split(/\n/, $text);    

    my $start = <<'EOQ';
sub {
my $data = shift(@_);
my $text = '';
EOQ

    my @mid = parse_code(\@lines);

    my $end .= <<'EOQ';
return $text;
}
EOQ

    my $code = join("\n", $start, @mid, $end);
    my $sub = eval ($code);
    die $@ unless $sub;

    return $sub;
}

#----------------------------------------------------------------------
# Do the search and build the output array

sub do_search {
    my ($base_url, $base_directory, @term) = @_;

    # Create the closure used to search the files

    my $results = [];
    my $do_pattern = globbify (DO_SEARCH);
    my $dont_pattern = globbify (DONT_SEARCH);

    my $searcher = sub {
        return if $do_pattern && ! /$do_pattern/o;
        return if $dont_pattern && /$dont_pattern/o;
    
        my $text = slurp($_);
        return unless $text;
        
        my ($title, $body) =  parse_htmldoc($text);
        return unless length ($body);
    
        my ($count, @pos);
        foreach my $term (@term) {
            my $pos = 0;
            while ($body =~ /$term/gi) {
                $pos ||= pos ($body);
                $count ++;
            }
    
            if ($pos) {
                push (@pos, $pos);
            } else {
                return;
            }
        }
    
        my $modtime = (stat $_)[9];
        my $result = {title => $title, count => $count, modtime => $modtime};
    
        $result->{url} = 
          build_url($base_url, $base_directory, $File::Find::name);
    
        $result->{context} = get_context($body, $term[0], $pos[0]),;
    
        push (@$results, $result);
    };

    # Search the directory tree

    find ($searcher, $base_directory) if @term;
    return $results;
}

#----------------------------------------------------------------------
# Add parameters to a url

sub encode_url {
    my $url = shift (@_);
    my (%param) = @_;

    my $arglist;
    foreach my $key (sort keys %param) {
        $arglist .= '&' if $arglist;

        my $value = $param{$key};
        $value =~ s/([&\+\"\'])/sprintf ('%%%02x', ord($1))/ge;
        $value =~ tr/ /+/;
	
        $arglist .= "$key=$value";
    }

    return $arglist ? "$url?$arglist" : $url;
}

#----------------------------------------------------------------------
# Get the context of a search term match

sub get_context {
    my ($text, $term, $pos) = @_;

    my $start = $pos - CONTEXT_LENGTH / 2;
    $start = 0 if $start < 0;

    my $end = $pos + CONTEXT_LENGTH / 2;
    my $len = ($end - $start) + 1;
    $len = length ($text) - $start if $len > length ($text) - $start;

    my $context = substr ($text, $start, $len);

    $context =~ s/^\S*\s+//g;
    $context =~ s/\s+\S*$//g;
    $context =~ s!($term)!<b>$1</b>!gi;
    $context =~ s/\s+/ /g;
    
    return $context;
}

#----------------------------------------------------------------------
# Convert filename wildcards into regexp wildcards

sub globbify {
    my ($pattern) = @_;

    my @pattern;
    if (ref $pattern) {
        @pattern = @$pattern;
    } else {
        push (@pattern, $pattern);
    }

    my %patmap = (
		    '*' => '.*',
		    '?' => '.',
		    '[' => '[',
		    ']' => ']',
		  );

    my @regexp;
    foreach my $pattern (@pattern) {
        next unless length ($pattern);
    
        $pattern =~ s/(.)/$patmap{$1} || "\Q$1"/ge;
        $pattern = '(^' . $pattern . '$)';
        push (@regexp, $pattern);
    }

    return join ('|', @regexp);
}

#----------------------------------------------------------------------
# Create urls for previous and next queries

sub navlinks {
    my ($hash) = @_;

    if ($hash->{start} > 1) {
	my $first = $hash->{start} - NUMBER_RESULTS;
	$first = 1 if $first < 1;

	$hash->{previous_url} = encode_url ($hash->{script_url}, 
					    START_PARAM, $first, 
					    QUERY_PARAM, $hash->{query});
    }

    if ($hash->{finish} < $hash->{total}) {
        $hash->{next_url} = encode_url ($hash->{script_url}, 
                        START_PARAM, $hash->{finish} + 1, 
                        QUERY_PARAM, $hash->{query});
    }
    
    return $hash;
}

#----------------------------------------------------------------------
# Parse the templace source

sub parse_code {
    my ($lines, $command) = @_;

    my @code;
    my @stash;

    while (defined (my $line = shift @$lines)) {
        my ($cmd, $cmdline) = parse_command($line);
    
        if (defined $cmd) {
            if (@stash) {
                push(@code, '$text .= <<"EOQ";', @stash, 'EOQ');
                @stash = ();
            }
            push(@code, $cmdline);
            
            if (substr($cmd, 0, 3) eq 'end') {
                my $startcmd = substr($cmd, 3);
                die "Mismatched block end ($command/$cmd)"
                      if defined $startcmd && $startcmd ne $command;
                return @code;

            } elsif (COMMANDS->{"end$cmd"}) {
                push(@code, parse_code($lines, $cmd));
            }
        
        } else {
            $line =~ s/(?<!\\)\$(\w+)/\$data->{$1}/g;
            push(@stash, $line);
        }
    }

    die "Missing end (end$command)" if $command;
    push(@code, '$text .= <<"EOQ";', @stash, 'EOQ') if @stash;

    return @code;
}

#----------------------------------------------------------------------
# Parse a command and its argument

sub parse_command {
    my ($line) = @_;

    return unless $line =~ s/^\s*<!--\s*//;

    $line =~ s/\s*-->//;
    my ($cmd, $arg) = split(' ', $line, 2);
    $arg = '' unless defined $arg;
    
    my $cmdline = COMMANDS->{$cmd};
    return unless $cmdline;
    
    $arg =~ s/([\@\%])(\w+)/$1\{\$$2\}/g;
    $arg =~ s/(?<!\\)\$(\w+)/\$data->{$1}/g;
    $cmdline =~ s/%%/$arg/; 

    return ($cmd, $cmdline);
}

#----------------------------------------------------------------------
# Get title and remove html from document

sub parse_htmldoc {
    my ($text) = @_;

    return $text unless length ($text);

    my ($title) = $text =~ m!<title>(.*)</title>!i;
    $title =~ tr/\t\r\n / /s;
    $title = '(No Title)' unless length ($title);
    
    my $body_tag = BODY_TAG;
    my $section = parse_sections($text);
    my $body = $section->{$body_tag} || '';
    $body =~ s/<[^>]*>//g;

    return ($title, $body);
}

#----------------------------------------------------------------------
# Extract sections from file, store in hash

sub parse_sections {
    my ($text) = @_;

    my $name;
    my %section;

    # Extract sections from input

    my @tokens = split (/(<!--\s*(?:section|endsection)\s+.*?-->)/, $text);

    foreach my $token (@tokens) {
        if ($token =~ /^<!--\s*section\s+(\w+).*?-->/) {
            if (defined $name) {
                die "Nested sections in input: $token\n";
            }
            $name = $1;
    
        } elsif ($token =~ /^<!--\s*endsection\s+(\w+).*?-->/) {
            if ($name ne $1) {
                die "Nested sections in input: $token\n";
            }
            undef $name;
    
        } elsif (defined $name) {
            $section{$name} = $token;
        }
    }
    
    die "Unmatched section (<!-- section $name -->)\n" if $name;
    return \%section;
}

#----------------------------------------------------------------------
# Sort and restrict the set of results

sub restrict_page {
    my ($hash, $results, $start) = @_;

    $hash->{total} =  @$results;

    $hash->{start} = $start || 1;

    $hash->{finish} = NUMBER_RESULTS + $hash->{start} - 1;
    $hash->{finish} = $hash->{total} if $hash->{finish} > $hash->{total};

    my $sorter = sub {
        $b->{count} <=> $a->{count} || $b->{modtime} <=> $a->{modtime}
    };

    @$results = sort $sorter @$results;

    my @restricted = @$results[$hash->{start}-1 .. $hash->{finish}-1];
    $hash->{results} = \@restricted;
    
    return $hash;
}

#----------------------------------------------------------------------
# Make sure there are no nasty characters in the query

sub scrub_parameter {
    my ($oldvalue) = @_;

    $oldvalue =~ /^([^\&\<\>]*)$/;
    my $newvalue = $1 || ''; 

    return $newvalue;
}

#----------------------------------------------------------------------
# Read a file into a string

sub slurp {
    my ($input) = @_;

    my $in;
    local $/;

    if (ref $input) {
        $in = $input;
    } else {
        $in = FileHandle->new ($input);
        return '' unless defined $in;
    }

    my $text = <$in>;
    $in->close;

    return $text;
}

#----------------------------------------------------------------------
# Substitue comment delimeted sections for same blacks in template

sub substitute_sections {
    my ($text, $section) = @_;

    my $name; 
    my @output;
    
    my @tokens = split (/(<!--\s*(?:section|endsection)\s+.*?-->)/, $text);

    foreach my $token (@tokens) {
        if ($token =~ /^<!--\s*section\s+(\w+).*?-->/) {
            if (defined $name) {
                die "Nested sections in template: $name\n";
            }

            $name = $1;
            push(@output, $token);
    
        } elsif ($token =~ /^\s*<!--\s*endsection\s+(\w+).*?-->/) {
            if ($name ne $1) {
                die "Nested sections in template: $name\n";
            }

            undef $name;
            push(@output, $token);
    
        } elsif (defined $name) {
            $section->{$name} ||= $token;
            push(@output, $section->{$name});
            
        } else {
            push(@output, $token);
        }
    }
    
    return join('', @output);
}

1;

__DATA__
<html>
<head>
<title>Site Search</title>
</head>
<body>
<!-- section content -->
<h2>Site Search</h2>
<div id="searchform">
<form method="post" action="$script_url">
<input type="text" name="$query_param" value="$query" size="40" />
</form>
</div>
<!-- if $query -->
<!-- if $total -->
<p>Documents $start to $finish of $total</p>
<!-- else -->
<p>No documents matched</p>
<!-- endif -->
<!-- else -->
<p>Enter one or more words to search for. The results will list pages
containing all the search terms. The match is case insensitive and
only matches entire words. To search for a phrase, enclose it "in
quotes".</p>
<!-- endif -->
<!-- for @results -->
<p><a href="$url"><b>$title</b></a><br />
$context</p>
<!-- endfor -->
<p>
<!-- if $previous_url -->
<a href="$previous_url"><b>Previous</b></a>
<!-- endif -->
<!-- if $next_url -->
<a href="$next_url"><b>Next</b></a>
<!-- endif -->
</p>
<!-- endsection content -->
</body>
</html>
