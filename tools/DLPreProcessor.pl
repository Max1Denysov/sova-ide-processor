#!/usr/bin/env perl

use strict;
use warnings;

use Data::Dumper;
use Clone;

use Algorithm::Combinatorics qw(permutations);

#
#	Препроцессор для обработки DL из АРМа, перед передачей его на компиляцию.
#

# Vars_counter.
my $VarsCounter = 0;


sub Exit {
	my $error = shift @_;
	print "ERROR: $error\n";
	exit(1);
}

# Вывод сообщение об ошибке.
sub ErrorMessage {
	print "file: ".shift."\n";
	print "  ERROR: ".shift."\n";
	print "  Id: ".shift."\n";
	print "  STRING: ".shift."\n";
}

# Вывод сообщение о предупреждении.
sub WarningMessage {
	print "file: ".shift."\n";
	print "  WARNING: ".shift."\n";
	print "  Id: ".shift."\n";
	print "  STRING: ".shift."\n";
}

# Препроцессирование одного файла с шаблонами.
sub ProcessDLFile {
	my ( $source, $target ) = @_;

	unless( open SOURCEFH, $source ) {
		Exit( "Can't open source file: $source" );
	}

	unless( open TARGETFH, ">$target" ) {
		Exit( "Can't open source file: $target" );
	}

	my $cmd = {};

	my $state = {
		'ACV' => {
			'name' => undef,
			'default' => undef
		},
		'AEXT' => undef,
		'IPC' => ''
	};

	my $pattern = undef;
	while( my $string = <SOURCEFH> ) {
		# Нормализация строки.
		chomp $string;
		$string =~ s/\s+/ /g;

		if( !$pattern && ( $string =~ /^\\\\/ || $string =~ /^\/\// || $string =~ /^\s*$/ ) ) {
			# Пропуск пустых строк и комментариев между шаблонами.
			print TARGETFH "$string\n";
		}
		elsif( $string =~ /^BEGIN\s+(.*?)\s*$/ ) {
			if( $pattern ) {
				ErrorMessage( $source, "END directive has missed.", $pattern->{id}, $string );
				# return 1;
				next;
			}
			else {
				$pattern->{'id'} = $1;
			}
		}
		elsif( $string =~ /^=/ ) {
			# Директива препроцессора.
			if( $string =~ /^=\s*#\s+ADD\s+(\w+)\s*:\s*(.*?)\s*$/i ) {
				if( $cmd->{$1} && $cmd->{$1}{'type'} ne '#' ) {
					WarningMessage( $source, "Preprocessor command with name $1 has redeclared with diffirent type.", $pattern ? $pattern->{id} : '', $string );
				}

				$cmd->{$1} = { 'type' => '#', 'cmd' => 'add', 'value' => $2 };
			}
			elsif( $string =~ /^=\s*#\s*GROUP\s+(\w+)\s*:\s*ONLYONE\s*$/i ) {
				if( $cmd->{$1} && $cmd->{$1}{'type'} ne '#' ) {
					WarningMessage( $source, "Preprocessor command with name $1 has redeclared with diffirent type.", $pattern ? $pattern->{id} : '', $string );
				}

				$cmd->{$1} = { 'type' => '#', 'cmd' => 'onlyone', 'var' => "\%auto_reg_var_$VarsCounter"  };
				$VarsCounter++;
			}
			elsif( $string =~ /^=\s*(ERASE|DELETE|DEL|UNSET)\s*(.*?)\s*$/ ) {
				unless( exists $cmd->{$2} ) {
					WarningMessage( $source, "Attempt to delete undefined command: $2", $pattern ? $pattern->{id} : '', $string );
				}
				delete $cmd->{$2};
			}
			else {
				ErrorMessage( $source, "Unknown preprocessor directive.", $pattern ? $pattern->{id} : '', $string );
				# return 1;
				next;
			}
		}
		elsif( $string =~ /^END\s*$/ ) {
			# Завершение шаблона.
			if( !$pattern ) {
				ErrorMessage( $source, "Unexpected end of pattern.", '', $string );
				# return 1;
				next
			}
			else {
				my $infs = {};
				foreach my $part ( @{$pattern->{'strings'}} ) {
					$infs->{$part->{'inf'}} = '';
				}

				# Разбор шаблона.
				foreach my $part ( @{$pattern->{'strings'}} ) {
					if( $part->{'inf'} eq '' ) {
						$pattern->{'common'} = 1;
					}
					if( $part->{'type'} eq '#' ) {
						if( $part->{'AEXT'} ) {
							$part->{'string'} .= " $part->{'AEXT'}";
						}

						foreach my $cmd ( keys %{$part->{'cmd'}} ) {
							if( $part->{'cmd'}{$cmd}{'type'} eq '#' ) {
								if( $part->{'cmd'}{$cmd}{'cmd'} eq 'add' ) {
									$part->{'string'} .= " $part->{'cmd'}{$cmd}{'value'}";
								}
								elsif( $part->{'cmd'}{$cmd}{'cmd'} eq 'onlyone' ) {
									$part->{'string'} = "# [IF(!$part->{'cmd'}{$cmd}{'var'})]{ ".substr( $part->{'string'}, 1 )." [$part->{'cmd'}{$cmd}{'var'}=\"1\"] }";
								}
							}
						}

						if( $part->{'ACV'}{'name'} ) {
							if( $part->{'ACV'}{'info'} ) {
								if( $part->{'string'} =~ /^#(\d)/ ) {
									$part->{'string'} = "# [IF(\%$part->{'ACV'}{'name'}=\"$1\")]{ ".substr( $part->{'string'}, 2 )." [%acv_info=\"$part->{'ACV'}{'name'}:$1\"] }";
								}
								elsif( defined $part->{'ACV'}{'default'} ) {
									$part->{'string'} = "# [IF(\%$part->{'ACV'}{'name'}=\"$part->{'ACV'}{'default'}\")]{ ".substr( $part->{'string'}, 1 )." [%acv_info=\"$part->{'ACV'}{'name'}:$part->{'ACV'}{'default'}\"] }";
								}
							}
							else {
								if( $part->{'string'} =~ /^#(\d)/ ) {
									$part->{'string'} = "# [IF(\%$part->{'ACV'}{'name'}=\"$1\")]{ ".substr( $part->{'string'}, 2 )." [%acv_info=\"\"] }";
								}
								elsif( defined $part->{'ACV'}{'default'} ) {
									$part->{'string'} = "# [IF(\%$part->{'ACV'}{'name'}=\"$part->{'ACV'}{'default'}\")]{ ".substr( $part->{'string'}, 1 )." [%acv_info=\"\"] }";
								}
							}
						}
						else {
							if( $part->{'string'} !~ /\[\%acv_info=""\]\s*$/ ) {
								$part->{'string'} .= " [%acv_info=\"\"]";
							}

						}

						if( $part->{'uniq'} ) {
							$part->{'string'} = "# [IF(!\%auto_reg_var_$VarsCounter)]{ ".substr( $part->{'string'}, 1 )." [\%auto_reg_var_$VarsCounter=\"1\"] }";
							$VarsCounter++;
						}
					}
					elsif( $part->{type} eq '$' ) {
						if( $part->{string} =~ /^(.*)(\[\@?(combine|cmb|combine_strict|combine_s|cmb_strict|cmb_s)\s*\()(.*)$/ ) {
							my $prefix = $1;
							my @cmb;
							my $string = $4;
							my $strict = $3 =~ /_s/;
							while( $string =~ /^,?\s*{\s*(([^}\\]|\\\\|\\}|\\\{|\\\[|\\]|\\<|\\>|\\\*)*)\s*}(.*)$/ ) {
								my $arg = $1;
								$string = $3;
								$arg =~ s/\\([\\{}[\]<>\*])/$1/g;
								push @cmb, $arg;
							}
							if( $string !~ /^\s*\)\s*](.*)$/ ) {
								ErrorMessage( $source, "Invalid function combine.", $pattern->{id}, $part->{string} );
								# return 1;
								next;
							}
							my $postfix = $1;
							if( $#cmb >= 5 ) {
								ErrorMessage( $source, "Invalid function combine. Too much elements.", $pattern->{id}, $part->{string} );
								# return 1;
								next;
							}
							my $it = permutations( \@cmb );
							$part->{string} = "";
							while( my $combination = $it->next() ) {
								$part->{string} .= "$prefix".join( ' '.( $strict ? '' : '*' ).' ', @$combination )."$postfix\n";
							}
						}
					}
					$infs->{$part->{'inf'}} .= "$part->{'string'}\n";
					if( $part->{'inf'} eq '' ) {
						foreach my $inf ( keys %{$infs} ) {
							next if( $inf eq '' );

							$infs->{$inf} .= "$part->{'string'}\n";
						}
					}
				}

				# Генерация шаблона.
				foreach my $inf ( keys %{$infs} ) {
					next if( $inf eq '' && !defined $pattern->{'common'} );
					if( $infs->{$inf} !~ /^\s*(\/\/.*)?$/ ) {
						print TARGETFH "BEGIN $pattern->{'id'}\n";
						if( $inf ne '' ) {
							print TARGETFH qq|+\%INF_PERSON="$inf"\n|;
						}
					}
					print TARGETFH $infs->{$inf};
					if( $infs->{$inf} !~ /^\s*(\/\/.*)?$/ ) {
						print TARGETFH "END\n";
					}
				}
				$pattern = undef;
			}
		}
		elsif( $string =~ /^--/ && $string !~ /^--(if|elsif|else|endif|switch|case|default|endswitch|label)/i ) {
			# Директива препроцессора.
			if( $string =~ /^--\s*SET\s+ANSWER\s+CONDITION\s+VARIABLE\s+NOINFO\s*=\s*(.*)\s*$/i || $string =~ /^--\s*SET\s+ACV\s+N\s*=\s*(.*)\s*$/i ) {
				$state->{'ACV'}{'name'} = $1;
				$state->{'ACV'}{'name'} =~ s/\s+/ /g;
				if( $state->{'ACV'}{'name'} =~ /^\s*$/ ) {
					$state->{'ACV'}{'name'} = undef;
				}
				$state->{'ACV'}{'info'} = 0;
			}
			elsif( $string =~ /^--\s*SET\s+ANSWER\s+CONDITION\s+VARIABLE\s*=\s*(.*)\s*$/i || $string =~ /^--\s*SET\s+ACV\s*=\s*(.*)\s*$/i ) {
				$state->{'ACV'}{'name'} = $1;
				$state->{'ACV'}{'name'} =~ s/\s+/ /g;
				if( $state->{'ACV'}{'name'} =~ /^\s*$/ ) {
					$state->{'ACV'}{'name'} = undef;
				}
				$state->{'ACV'}{'info'} = 1;
			}
			elsif( $string =~ /^--\s*SET\s+ANSWER\s+CONDITION\s+VALUE\s+DEFAULT\s*=\s*(.*?)\s*$/i || $string =~ /^--\s*SET\s+ACV\s+DEFAULT\s*=\s*(.*?)\s*$/i ) {
				$state->{'ACV'}{'default'} = $1;
				$state->{'ACV'}{'default'} =~ s/\s+/ /g;
				if( $state->{'ACV'}{'default'} =~ /^\s*$/ ) {
					$state->{'ACV'}{'default'} = undef;
				}
			}
			elsif( $string =~ /^--\s*UNSET\s+ANSWER\s+CONDITION\s+VARIABLE\s*$/i || $string =~ /^--\s*UNSET\s+ACV\s*$/ ) {
				$state->{'ACV'}{'name'} = undef;
			}
			elsif( $string =~ /^--\s*UNSET\s+ANSWER\s+CONDITION\s+VALUE\s+DEFAULT\s*$/i || $string =~ /^--\s*UNSET\s+ACV\s+DEFAULT\s*$/ ) {
				$state->{'ACV'}{'default'} = undef;
			}
			elsif( $string =~ /^--\s*SET\s+ANSWER\s+EXTENSION\s*=\s*(.*?)\s*$/i || $string =~ /^--\s*SET\s+AEXT\s*=\s*(.*?)\s*$/i ) {
				$state->{'AEXT'} = $1;
			}
			elsif( $string =~ /^--\s*UNSET\s+ANSWER\s+EXTENSION\s*$/i || $string =~ /^--\s*UNSET\s+AEXT\s*$/i ) {
				$state->{'AEXT'} = undef;
			}
			elsif( $string =~ /^--\s*INF\s*=\s*(\w+?)\s*$/ ) {
				$state->{'IPC'} = $1;
			}
			elsif( $string =~ /^--\s*INF\s*=?\s*\*\s*$/ ) {
				$state->{'IPC'} = '';
			}
			else {
				ErrorMessage( $source, "Invalid preprocessor command.", $pattern ? $pattern->{id} : '', $string );
				# return 1;
				next;
			}
		}
		else {
			my $type = substr( $string, 0, 1 );

			# Проверка на продолжение предыдущей строки.
			if( $type eq ' ' ) {
				if( $#{$pattern->{'strings'}} == -1 ) {
					ErrorMessage( $source, "Invalid string continuation.", $pattern ? $pattern->{id} : '', $string );
					# return 1;
					next;
				}
				else {
					$pattern->{'strings'}[$#{$pattern->{'strings'}}]->{'string'} .= "\n$string";
				}
			}
			else {
				my $uniqFlag = 0;
				if( $string =~ /^#(uniq|u)[#:](.*)$/ ) {
					$uniqFlag = 1;
					$string = "#$2";
				}

				push @{$pattern->{'strings'}}, {
						'type' => $type,
						'inf' => $state->{'IPC'},
						'string' => $string,
						'ACV' => {
							'name' => $state->{'ACV'}{'name'},
							'default' => $state->{'ACV'}{'default'},
							'info' => $state->{'ACV'}{'info'}
						},
						'AEXT' => $state->{'AEXT'},
						'uniq' => $uniqFlag,
						'cmd' => Clone::clone($cmd)
					};
			}
		}
	}
	close SOURCEFH;
	close TARGETFH;

	return 0;
}


my $DLFileList = "dl.lst";
my $RootPath = $ARGV[0];
unless( defined $RootPath ) {
	$RootPath = '.';
}

unless( chdir( $RootPath ) ) {
	Exit( "Can't chdir $RootPath: $!" );
}

unless( open( LISTFH, $DLFileList ) ) {
	Exit( "Can't open file $DLFileList: $!" );
}

while( my $line2 = <LISTFH> ) {
	next if( $line2 =~ /^\s*$/ || $line2 =~ /^\s*\\\\/ );

	chomp $line2;
	$line2 =~ s/\s*$//g;
	my $target = "$line2.tmp.$$.".time;
	if( ProcessDLFile( $line2, $target ) == 0 ) {
		`mv "$target" "$line2"`;
	}
	else {
		`rm "$target"`;
	}
}

close LISTFH;


exit( 0 );
