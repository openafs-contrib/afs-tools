#!/usr/bin/perl

# Copyright (c) 2010, Sine Nomine Associates
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
# Originally written by Andrew Deason <adeason@sinenomine.net>

=head1 NAME

cw_graphify.pl - Turn 'calls waiting' Nagios logs into graphs

=head1 SYNOPSIS

B<cw_graphify.pl> <B<--monthly> | B<--daily> | B<--hourly> | B<--all>>
                  <B<--line> | B<--impulse> | B<--histogram>>
                  [B<--plot> <I<plotfile.plt>>] [B<--data> <I<datafile.dat>>]
                  [B<--graph> <I<graphfile.png>>] [B<--in>] <I<logfile.log>>
                  [B<--extended>] [B<--maxy> <I<maxyvalue>>]

=head1 DESCRIPTION

B<cw_graphify.pl> takes Nagios logs that report the number of calls waiting
for various servers, and turns them into various kinds of graphs. The log
input must look like this:

   2009 11 03 04:05 afs1: 0 calls waiting 123 idle threads
   2009 11 03 04:05 afs2: 12 calls waiting 2 idle threads
   2009 11 03 04:05 afs3: 0 calls waiting 120 idle threads
   2009 11 03 04:05 afs4: 0 calls waiting 123 idle threads
   2009 11 03 04:10 afs1: 0 calls waiting 123 idle threads
   2009 11 03 04:10 afs2: 103 calls waiting 2 idle threads
   2009 11 03 04:10 afs3: 0 calls waiting 122 idle threads

Note that there B<must be no duplicate lines> for the graphed data to be
accurate (pipe through `sort | uniq' if you're not sure). Currently
anything beyond 'X calls waiting' is ignored, though the idle thread
could probably also be useful in making graphs.

=head1 OPTIONS

=over 4

=item B<--monthly>

Graphs the number of 'calls waiting' for each server in each month in the
given data. All of the 'calls waiting' for each entire month are added
together, and the result is what appears on the graph.

=item B<--daily>

Same as B<--monthly>, but for every day instead of every month.

=item B<--hourly>

Same as B<--monthly>, but for every hour instead of every month.

=item B<--all>

Graphs the number of 'calls waiting' for every single line in the given
log input.

=item B<--line>

Creates a line graph.

=item B<--impulse>

Graphs each 'calls waiting' value as a vertical line, whose height is
equal to how many calls waiting there were. This is probably only useful
when used with B<--all>.

=item B<--histogram>

Graphs the number of calls waiting for the given time period as a stacked
histogram. Each server in the log input is a different area on the
histogram, and the total height of each box is the sum of all calls
waiting on all servers.

This option does not work with gnuplot 4.2, but does with gnuplot 4.4.

=item B<--plot> <I<plotfile.plt>>

Specifies the .plt file to generate. Run C<gnuplot> on this file
after running B<cw_graphify.pl> to generate the graph.

If not specified, it defaults to <I<type>>-<I<time>>-<I<logfile>>.png, where
<I<type>> is line, impulse, etc; <I<time>> is monthly, daily, etc; and
<I<logfile>> is the input logfile filename with its file extension removed
(if it has any).

=item B<--data> <I<datafile.dat>>

Specifies the .dat file to generate, which will contain the
tab-delimited data needed by the .plt file to generate the desired graph.

If not specified, it defaults to the same value as B<--plot>, except with
a .dat file extension instead of .plt.

=item B<--graph> <I<graphfile.png>>

Specifies the file name of the resultant graph PNG. If not specified,
it defaults to the same value as B<--plot>, except with a .png file
extension instead of .plt.

=item [B<--in>] <I<logfile.log>>

Specifies the log file that contains the 'calls waiting' data to graph.
It must be specified.

=item B<--extended>

Indicates to use some extra features of gnuplot that may not exist in
versions prior to gnuplot 4.4, to make the graphs look slightly prettier.
Currently, enabling this only tilts the xtic labels, but it perhaps
should enable more.

=item B<--maxy> <I<maxyvalue>>

Caps the Y value of the result graph at <I<maxyvalue>>. Use this if
spikes in the data are obscuring the rest of the graph data. For example,
if most of your data is below 20,000, but there is one spike at 100,000
that is screwing up the scale, pass `--maxy 20000' to make the non-spike
data more viewable.

=back

=head1 EXAMPLES

   $ ../cw_graphify.pl --impulse --all --in afs-stats.0911
   
   Aggregate data has been output to impulse-all-afs-stats.0911.dat, and a gnuplot
   script has been output to impulse-all-afs-stats.0911.plt. Now you can run
   
   gnuplot impulse-all-afs-stats.0911.plt
   
   and/or tweak impulse-all-afs-stats.0911.plt to your tastes, in order to produce
   the desired graph. Unmodified, the supplied gnuplot script will produce
   a graph in the file
   
   impulse-all-afs-stats.0911.png
   
   $ gnuplot impulse-all-afs-stats.0911.plt
   $ xli impulse-all-afs-stats.0911.png

=head1 COPYRIGHT

Sine Nomine Associates 2010. <http://www.sinenomine.net> All Rights Reserved.

=cut

use strict;
use Getopt::Long;
use File::Spec;

sub usage() {
	my $len = length $0;
	print STDERR "Usage: $0 <--monthly | --daily | --hourly | --all>\n";
	print STDERR (' 'x($len+8)) . "<--line | --impulse | --histogram>\n";
	print STDERR (' 'x($len+8)) .
		"[--plot calls.plt] [--data calls.dat]\n";
	print STDERR (' 'x($len+8)) .
		"[--graph calls.png] [--in] calls.log\n";
	print STDERR (' 'x($len+8)) .
		"[--extended] [--maxy maxyvalue]\n";
	print STDERR "\nSee 'perldoc cw_graphify.pl' for more information.\n\n";
}

sub sum(@) {
	my $sum = 0;
	$sum += $_ for @_;
	return $sum;
}

sub hashstr($) {
	my ($hashP) = @_;
	my %hash = %$hashP;
	for (keys %hash) {
		if ($hash{$_}) {
			return $_;
		}
	}
	die('internal error');
}

sub newsuffix($$$$) {
	my ($typesP, $timesP, $path, $suffix) = @_;
	my $typestr = hashstr($typesP);
	my $timestr = hashstr($timesP);

	my ($unused, $dir, $file) = File::Spec->splitpath($path);

	if ($dir =~ m/\/$/) {
		chop $dir;
	}
	if (length $dir == 0) {
		$dir = ".";
	}

	$file =~ s/\....$/./;

	return "$dir/$typestr-$timestr-$file.$suffix";
}

my %times = ('monthly' => 0, 'daily' => 0, 'hourly' => 0, 'all' => 0);
my %types = ('line' => 0, 'impulse' => 0, 'histogram' => 0);

my $infile = undef;
my $plotfile = undef;
my $datafile = undef;
my $graphfile = undef;
my $extended = 0;
my $maxy = 0;

if (not GetOptions("monthly"   => \$times{'monthly'},
                   "daily"     => \$times{'daily'},
                   "hourly"    => \$times{'hourly'},
                   "all"       => \$times{'all'},
                   "line"      => \$types{'line'},
                   "impulse"   => \$types{'impulse'},
                   "histogram" => \$types{'histogram'},
                   "in=s"      => \$infile,
                   "plot=s"    => \$plotfile,
                   "data=s"    => \$datafile,
                   "graph=s"   => \$graphfile,
                   "extended"  => \$extended,
                   "maxy=i"    => \$maxy,
                  )) {

	usage();
	exit(1);
}

if (sum(values %times) != 1) {
	print STDERR "You must specify one and only one time duration.\n";
	usage();
	exit(1);
}
if (sum(values %types) != 1) {
	print STDERR "You must specify one and only one graph type.\n";
	usage();
	exit(1);
}

if (!defined($infile)) {
	$infile = shift;
}
if (!defined($infile) || $#ARGV > 0) {
	print STDERR "Too many or too few arguments\n";
	usage();
	exit(1);
}

if (!defined($plotfile)) {
	$plotfile = newsuffix(\%types, \%times, $infile, 'plt');
}
if (!defined($datafile)) {
	$datafile = newsuffix(\%types, \%times, $infile, 'dat');
}
if (!defined($graphfile)) {
	$graphfile = newsuffix(\%types, \%times, $infile, 'png');
}

my @rows;
my %machines;

open(IN, "<$infile") or die("$infile: $!");
open(PLT, ">$plotfile") or die("$plotfile: $!");
open(DAT, ">$datafile") or die("$datafile: $!");

while (<IN>) {
	my ($year, $month, $day, $hour, $minute) = ('0001','01','01','00','00');
	my ($machine, $calls);
	my $time;

	if (not m/^(\d{4}) (\d{2}) (\d{2}) (\d{2}):(\d{2}) ([^:]+): ([0-9][0-9]*) calls waiting .*$/) {
		if (m/network timeout after 20 seconds/) {
			# noop
		} elsif (m/cannot contact server/) {
			# noop
		} else {
			print STDERR "unmatched line: $_\n";
		}
		next;
	}

	$year = $1;
	$month = $2;

	$machine = $6;
	$calls = $7;

	if (!$times{'monthly'}) {
		$day = $3;
		if (!$times{'daily'}) {
			$hour = $4;
			if (!$times{'hourly'}) {
				$minute = $5;
			}
		}
	}

	$time = "$year-$month-$day $hour:$minute";

	if (!defined($machines{$machine})) {
		$machines{$machine} = {};
	}

	my $isin = 0;
	for my $_time (@rows) {
		if ($_time eq $time) {
			$isin = 1;
			last;
		}
	}

	if (!$isin) {
		push @rows, $time;
	}

	if (!defined($machines{$machine}->{$time})) {
		$machines{$machine}->{$time} = 0;
	}

	$machines{$machine}->{$time} += $calls;
}

close(IN);

my @machlist = grep {
	my $ret = 0;
	for my $time (@rows) {
		my $calls = $machines{$_}->{$time};
		if (defined($calls) and $calls > 0) {
			$ret = 1;
			last;
		}
	}
	$ret;
} (keys %machines);

print DAT "Time";
for my $machine (@machlist) {
	print DAT "\t$machine";
}
print DAT "\n";

for my $time (@rows) {
	my $_time = $time;
	$_time =~ s/[^0-9]//g;
	if ($types{'histogram'}) {
		chop $_time;
		chop $_time;
	}
	print DAT "$_time";
	for my $machine (@machlist) {
		my $calls = 0;
		if (defined($machines{$machine}->{$time})) {
			$calls = $machines{$machine}->{$time};
		}
		print DAT "\t$calls";
	}
	print DAT "\n";
}

close(DAT);

my $width;

if ($types{'impulse'}) {
	$width = $#rows + 250;
} else {
	$width = $#rows * 30 + 300;
}

print PLT <<EOS;
set ylabel 'Calls Waiting'
set term png size $width,700
set grid ytics
set bmargin 6

set output '$graphfile'

set key autotitle columnheader
set key outside invert samplen 4 spacing 1 width 0 height 0 

EOS

if ($maxy > 0) {
	print PLT "set yrange [0:$maxy]\n";
}

if ($types{'line'}) {
	print PLT "set style data lines\n";
} elsif ($types{'impulse'}) {
	print PLT "set style data impulses\n";
} elsif ($types{'histogram'}) {
	print PLT <<EOS;
set style data histogram;

set boxwidth 0.75 absolute
set style fill solid 1.00 border -1
set style histogram rowstacked title  offset character 0, 0, 0
set xtics border out nomirror rotate by -45 offset character 0,0 font "Vera,8"

datelab(N) = \\
	sprintf("%0.4d-%0.2d-%0.2d %0.2d:00", (N / 1000000), (N / 10000) % 100, (N / 100) % 100, N % 100)
EOS
}

my $maxmachindex = $#machlist + 2;

if ($types{'histogram'}) {
	print PLT "plot \"$datafile\" using 2:xticlabel(datelab(int(column(1))))";
	for my $i (3..$maxmachindex) {
		print PLT ",\\\n'' using $i:xticlabel(datelab(int(column(1))))";
	}
	print PLT "\n";

} else {
	if ($extended) {
		print PLT "set xtics border out nomirror rotate by -45 font \"Vera,8\"\n";
	} else {
		print PLT "set xtics border out nomirror rotate font \"Vera,8\"\n";
	}

	print PLT <<EOS;
set xdata time
set timefmt "%Y%m%d%H%M"
EOS

	print PLT "plot \"$datafile\" using 1:2";
	for my $i (3..$maxmachindex) {
		print PLT ",\\\n'' using 1:$i";
	}
	print PLT "\n";
}
close(PLT);

print <<EOS;

Aggregate data has been output to $datafile, and a gnuplot
script has been output to $plotfile. Now you can run

gnuplot $plotfile

and/or tweak $plotfile to your tastes, in order to produce
the desired graph. Unmodified, the supplied gnuplot script will produce
a graph in the file

$graphfile

EOS
