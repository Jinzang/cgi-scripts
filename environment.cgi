#!/usr/bin/perl

=pod

=head1 NAME

environment.cgi -- Display environment variables seen by cgi script

=head1 AUDIENCE

This script is intended for web masters who are initially setting up a
web site. It displays the environment variables that are available to a
script. It should be installed on the new site and then deleted after
it is run.

=head1 INSTALLATION

Before installing the script, you should find out from your ISP what
extension should be used for a Perl cgi script and what is the
location of Perl on your ISP's system. This information will probably
be available in the FAQ. If the top line of this file does not match
the location of Perl on your ISP's system, edit it so it does.

Ftp this file onto your web site and then use the ftp client to give this
file executable permission. Once all
that is done, run the script by typing its url, something like

http://www.yoursite.com/environment.cgi

The script should display the enviornment variables a cgi script will
see on your site. If it does not run, double check the first line, the
permissions on the script, and make sure your web sete is configured
correctly to run cgi scripts with the .cgi extension.

=head1 CUSTOMIZATION

You may want to change the way the output looks. You can do this by editing
the configuration variables and by creating html template files
for the search engine.

The template can be customized to make it look the way you wish. The template
commands and variables are described in the next section.

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

=item name

The name of the environment variable

=item value

The value of the enivronment variable.

=back

=head1 AUTHOR

Bernie Simon (bernie.simon@gmail.com)
 
=head1 LICENSE

Copyright Bernard Simon, 2014 under the Perl Artistic License.

=cut

package SearchEngine;

use strict;
use warnings;

use Cwd;
use English;
use FileHandle;

our $VERSION = '0.11';

#----------------------------------------------------------------------
# Configuration variables

# Template used to display results
use constant SEARCH_TEMPLATE => '';

# Template used to give page the site's look
use constant SITE_TEMPLATE => '';

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
    
    # Convert the environment variables to a list of hashes
    
    my @vars;
    my $hash = {};
    
    # Extra environment variables
    
    $ENV{PERL_VERSION} = $PERL_VERSION;
    $ENV{CURRENT_DIRECTORY} = getcwd();
    
    foreach my $name (sort keys %ENV) {
        push(@vars, {name => $name, value => $ENV{$name}});
    }

    $hash->{vars} = \@vars;
    
    # Figure out which templates we have, put them in a list
    
    my @templates;
    push(@templates, SITE_TEMPLATE) if SITE_TEMPLATE;
    
    if (SEARCH_TEMPLATE) {
        push(@templates, SEARCH_TEMPLATE);
    } else {
        push(@templates, \*DATA);
    }

    # Generate output page and print it

    my $sub = compile_code(@templates);
    my $output = &$sub($hash);
        
    print "Content-type: text/html\n\n";
    print $output;
    return;
}

#----------------------------------------------------------------------
# Compile a template into a subroutine which when called fills itself

sub compile_code {
    my (@templates) = @_;

    # Template precedes subtemplate, which precedes subsubtemplate

    my $text;
    my $section = {};
    while (my $template = pop(@templates)) {
        # If a template contains a newline, it is a string,
        # if not, it is a filename

        $text = slurp($template);
        $text = substitute_sections($text, $section);
    }

    return construct_code($text);
}

#----------------------------------------------------------------------
# Compile a subroutine from the code embedded in the template

sub construct_code {
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
<title>CGI Environment</title>
</head>
<body>
<!-- section content -->
<h2>CGI Environment</h2>

<!-- for @vars -->
<div class="entry"><b>$name</b> $value</div>
<!-- endfor -->
<!-- endsection content -->
</body>
</html>
